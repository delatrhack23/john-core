#!/usr/bin/env python3
"""
Jeu pedagogique de trading en bourse (marche fictif) - interface stylee
avec la bibliotheque "rich" (panneaux, couleurs, tableaux).

But: apprendre les bases du trading (achat/vente, gestion du risque,
stop-loss, diversification) SANS RISQUER D'ARGENT REEL. Aucune connexion
a un vrai broker, aucune vraie donnee de marche: tout est simule.

Installation:
    pip install -r requirements.txt

Comment jouer:
    python3 trading_game.py

    A chaque "jour" de bourse, les prix des actions fictives evoluent.
    Des actualites aleatoires peuvent faire monter ou descendre un
    secteur ou une action. Vous partez avec un capital de depart et
    devez le faire fructifier en achetant/vendant intelligemment.

Commandes disponibles pendant une journee:
    acheter TICKER QTE    (alias: buy)
    vendre TICKER QTE     (alias: sell)
    stop TICKER PRIX      pose un ordre stop-loss (vente auto si le prix
                           tombe a ce niveau ou en dessous)
    annulerstop TICKER    annule un stop-loss existant
    info TICKER           affiche des details qualitatifs sur une action
    portefeuille          affiche votre portefeuille (alias: portfolio)
    aide                  affiche l'aide (alias: help)
    suivant               passe au jour suivant (alias: next)
    quitter               termine la partie immediatement (alias: quit)

Options:
    --days N        nombre de jours de bourse a jouer (defaut: 20)
    --capital N     capital de depart en euros (defaut: 10000)
    --seed N        graine aleatoire pour rejouer exactement la meme partie
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass, field

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align
    from rich.box import ROUNDED, HEAVY
    from rich.prompt import Prompt
    from rich.console import Group
except ImportError as exc:
    raise SystemExit(
        "La bibliotheque 'rich' est requise pour l'interface stylee de ce jeu.\n"
        "Installez-la avec: pip install -r requirements.txt"
    ) from exc


ACCENT = "bright_magenta"
ACCENT_DIM = "magenta"
POSITIVE = "bright_green"
NEGATIVE = "bright_red"
NEUTRAL = "grey70"

SPARK_CHARS = "▁▂▃▄▅▆▇█"

console = Console()


def money(value: float) -> str:
    return f"{value:,.2f} EUR".replace(",", " ")


def pct_style(value: float) -> str:
    if value > 0:
        return POSITIVE
    if value < 0:
        return NEGATIVE
    return NEUTRAL


def pct_arrow(value: float) -> str:
    if value > 0:
        return "▲"
    if value < 0:
        return "▼"
    return "▬"


@dataclass
class Stock:
    ticker: str
    name: str
    sector: str
    price: float
    drift: float       # tendance moyenne par jour (ex: 0.003 = +0.3%/jour en moyenne)
    volatility: float  # amplitude des variations aleatoires quotidiennes
    history: list[float] = field(default_factory=list)

    def step(self) -> None:
        """Fait evoluer le prix d'un jour (marche aleatoire avec tendance)."""
        shock = random.gauss(self.drift, self.volatility)
        self.price = max(0.5, round(self.price * (1 + shock), 2))
        self.history.append(self.price)

    def apply_shock(self, multiplier: float) -> None:
        """Applique un choc immediat (actualite) au prix."""
        self.price = max(0.5, round(self.price * multiplier, 2))
        if self.history:
            self.history[-1] = self.price

    def volatility_label(self) -> str:
        if self.volatility < 0.02:
            return "faible"
        if self.volatility < 0.04:
            return "moyenne"
        return "elevee"

    def sparkline(self, width: int = 20) -> str:
        values = self.history[-width:]
        if len(values) < 2:
            return "(pas assez d'historique)"
        lo, hi = min(values), max(values)
        span = hi - lo or 1.0
        return "".join(
            SPARK_CHARS[min(len(SPARK_CHARS) - 1, int((v - lo) / span * (len(SPARK_CHARS) - 1)))]
            for v in values
        )


def build_market(seed: int | None) -> dict[str, Stock]:
    if seed is not None:
        random.seed(seed)
    return {
        "TCH": Stock("TCH", "TechNova", "Technologie", 120.0, 0.0040, 0.035),
        "BNK": Stock("BNK", "SolidBank", "Finance", 60.0, 0.0010, 0.015),
        "NRG": Stock("NRG", "GreenEnergie", "Energie", 45.0, 0.0060, 0.050),
        "FUD": Stock("FUD", "AgroPlus", "Consommation", 30.0, 0.0015, 0.012),
        "BIO": Stock("BIO", "MedBio", "Sante", 80.0, 0.0030, 0.045),
    }


NEWS_TEMPLATES = [
    ("{name} annonce des resultats records ce trimestre !", 1.10, 1.20),
    ("{name} est visee par une enquete reglementaire.", 0.80, 0.92),
    ("Rumeur de rachat de {name} par un grand groupe.", 1.08, 1.15),
    ("{name} subit une panne majeure de production.", 0.85, 0.95),
    ("Le secteur {sector} beneficie d'une nouvelle reglementation favorable.", 1.05, 1.12),
    ("Le secteur {sector} souffre d'une hausse des taux d'interet.", 0.90, 0.97),
    ("{name} devoile un partenariat strategique inattendu.", 1.04, 1.10),
    ("Une rumeur non confirmee fait chuter {name}.", 0.88, 0.96),
]


def maybe_trigger_news(market: dict[str, Stock]) -> str | None:
    if random.random() > 0.45:
        return None
    template, lo, hi = random.choice(NEWS_TEMPLATES)
    multiplier = random.uniform(lo, hi)
    if "{sector}" in template and "{name}" not in template:
        sector = random.choice(list({s.sector for s in market.values()}))
        affected = [s for s in market.values() if s.sector == sector]
        for stock in affected:
            stock.apply_shock(multiplier)
        return template.format(sector=sector)
    stock = random.choice(list(market.values()))
    stock.apply_shock(multiplier)
    return template.format(name=stock.name, sector=stock.sector)


@dataclass
class Player:
    cash: float
    holdings: dict[str, int] = field(default_factory=dict)
    stop_orders: dict[str, float] = field(default_factory=dict)
    net_worth_history: list[float] = field(default_factory=list)
    tickers_ever_held: set[str] = field(default_factory=set)
    used_stop_loss: bool = False

    def net_worth(self, market: dict[str, Stock]) -> float:
        return self.cash + sum(qty * market[t].price for t, qty in self.holdings.items())

    def buy(self, market: dict[str, Stock], ticker: str, qty: int) -> tuple[bool, str]:
        if ticker not in market:
            return False, f"Ticker inconnu : {ticker}"
        if qty <= 0:
            return False, "Quantite invalide."
        cost = market[ticker].price * qty
        if cost > self.cash:
            return False, f"Fonds insuffisants (cout {money(cost)}, cash disponible {money(self.cash)})."
        self.cash -= cost
        self.holdings[ticker] = self.holdings.get(ticker, 0) + qty
        self.tickers_ever_held.add(ticker)
        return True, f"Achete {qty} x {ticker} a {money(market[ticker].price)} (total {money(cost)})."

    def sell(self, market: dict[str, Stock], ticker: str, qty: int) -> tuple[bool, str]:
        if ticker not in market:
            return False, f"Ticker inconnu : {ticker}"
        held = self.holdings.get(ticker, 0)
        if qty <= 0:
            return False, "Quantite invalide."
        if qty > held:
            return False, f"Vous ne possedez que {held} x {ticker}."
        revenue = market[ticker].price * qty
        self.cash += revenue
        self.holdings[ticker] -= qty
        if self.holdings[ticker] == 0:
            del self.holdings[ticker]
            self.stop_orders.pop(ticker, None)
        return True, f"Vendu {qty} x {ticker} a {money(market[ticker].price)} (total {money(revenue)})."

    def check_stop_orders(self, market: dict[str, Stock]) -> list[str]:
        messages = []
        for ticker in list(self.stop_orders.keys()):
            threshold = self.stop_orders[ticker]
            if ticker in self.holdings and market[ticker].price <= threshold:
                qty = self.holdings[ticker]
                _, msg = self.sell(market, ticker, qty)
                self.used_stop_loss = True
                messages.append(f"STOP-LOSS sur {ticker} (seuil {money(threshold)}) -> {msg}")
        return messages


def render_banner(days: int, starting_capital: float) -> None:
    title = Text("◆ TRADING SIMULATOR ◆", style=f"bold {ACCENT}", justify="center")
    subtitle = Text(
        f"Marche 100% fictif  •  {days} jours de bourse  •  Capital de depart {money(starting_capital)}",
        style=f"italic {NEUTRAL}",
        justify="center",
    )
    console.print(
        Panel(
            Align.center(Text.assemble(title, "\n", subtitle)),
            border_style=ACCENT,
            box=HEAVY,
            padding=(1, 4),
        )
    )


def render_day_header(day: int, total_days: int) -> None:
    progress = int((day / total_days) * 20)
    bar = "█" * progress + "░" * (20 - progress)
    header = Text.assemble(
        ("JOUR ", f"bold {NEUTRAL}"),
        (f"{day}", f"bold {ACCENT}"),
        (f" / {total_days}   ", f"bold {NEUTRAL}"),
        (bar, ACCENT_DIM),
    )
    console.print(Panel(header, border_style=ACCENT_DIM, box=ROUNDED, padding=(0, 2)))


def render_news(headline: str) -> None:
    console.print(
        Panel(
            Text(headline, style="bold yellow"),
            title="[bold yellow]◆ ACTUALITE ◆[/bold yellow]",
            border_style="yellow",
            box=ROUNDED,
        )
    )


def render_stop_loss_messages(messages: list[str]) -> None:
    for message in messages:
        console.print(Panel(Text(message, style=f"bold {NEGATIVE}"), border_style=NEGATIVE, box=ROUNDED))


def render_market(market: dict[str, Stock], previous_prices: dict[str, float]) -> None:
    table = Table(
        title="[bold]Marche[/bold]", box=ROUNDED, border_style=ACCENT_DIM, header_style=f"bold {ACCENT}",
        expand=True,
    )
    table.add_column("Ticker", style="bold white")
    table.add_column("Nom")
    table.add_column("Secteur", style=NEUTRAL)
    table.add_column("Prix", justify="right")
    table.add_column("Variation", justify="right")

    for ticker, stock in market.items():
        prev = previous_prices.get(ticker, stock.price)
        change_pct = (stock.price - prev) / prev * 100 if prev else 0.0
        style = pct_style(change_pct)
        change_txt = f"{pct_arrow(change_pct)} {change_pct:+.2f}%"
        table.add_row(
            ticker,
            stock.name,
            stock.sector,
            money(stock.price),
            Text(change_txt, style=style),
        )
    console.print(table)


def render_portfolio(player: Player, market: dict[str, Stock], starting_capital: float) -> None:
    net_worth = player.net_worth(market)
    total_return = (net_worth - starting_capital) / starting_capital * 100
    style = pct_style(total_return)

    table = Table(box=ROUNDED, border_style="cyan", header_style="bold cyan", expand=True)
    table.add_column("Position", style="bold white")
    table.add_column("Quantite", justify="right")
    table.add_column("Valeur", justify="right")
    table.add_column("Stop-loss", justify="right", style=NEGATIVE)

    if not player.holdings:
        table.add_row("[dim]aucune position[/dim]", "-", "-", "-")
    else:
        for ticker, qty in player.holdings.items():
            value = qty * market[ticker].price
            stop = player.stop_orders.get(ticker)
            table.add_row(ticker, str(qty), money(value), money(stop) if stop else "-")

    footer = Text.assemble(
        ("Cash disponible : ", "bold white"), (money(player.cash), "white"),
        ("   |   Valeur totale : ", "bold white"), (money(net_worth), "bold white"),
        ("   (", NEUTRAL), (f"{pct_arrow(total_return)} {total_return:+.2f}%", f"bold {style}"), (")", NEUTRAL),
    )

    console.print(
        Panel(
            Group(table, footer),
            title="[bold cyan]◆ Portefeuille ◆[/bold cyan]",
            border_style="cyan",
            box=ROUNDED,
        )
    )


def render_help() -> None:
    table = Table(box=ROUNDED, border_style=ACCENT_DIM, header_style=f"bold {ACCENT}", show_header=True)
    table.add_column("Commande", style="bold white")
    table.add_column("Description")
    rows = [
        ("acheter TICKER QTE  (buy)", "Acheter des actions"),
        ("vendre TICKER QTE  (sell)", "Vendre des actions"),
        ("stop TICKER PRIX", "Poser un ordre stop-loss"),
        ("annulerstop TICKER", "Annuler un stop-loss"),
        ("info TICKER", "Details sur une action"),
        ("portefeuille  (portfolio)", "Voir son portefeuille"),
        ("aide  (help)", "Afficher cette aide"),
        ("suivant  (next)", "Passer au jour suivant"),
        ("quitter  (quit)", "Terminer la partie"),
    ]
    for cmd, desc in rows:
        table.add_row(cmd, desc)
    console.print(Panel(table, title=f"[bold {ACCENT}]◆ Commandes ◆[/bold {ACCENT}]", border_style=ACCENT))


def render_info(stock: Stock) -> None:
    body = Text.assemble(
        (f"{stock.name} ", "bold white"), (f"({stock.ticker})\n", NEUTRAL),
        ("Secteur     : ", "bold white"), (f"{stock.sector}\n", "white"),
        ("Prix actuel : ", "bold white"), (f"{money(stock.price)}\n", "white"),
        ("Volatilite  : ", "bold white"), (f"{stock.volatility_label()}\n", "white"),
        ("Historique  : ", "bold white"), (stock.sparkline(), ACCENT),
    )
    console.print(Panel(body, border_style=ACCENT_DIM, box=ROUNDED))


def render_feedback(success: bool, message: str) -> None:
    style = POSITIVE if success else NEGATIVE
    console.print(f"  [{style}]{'✔' if success else '✘'} {message}[/{style}]")


def handle_command(command: str, player: Player, market: dict[str, Stock]) -> str | None:
    """Traite une commande. Retourne 'next', 'quit', ou None pour continuer."""
    parts = command.strip().lower().split()
    if not parts:
        return None
    action = parts[0]

    if action in ("suivant", "next"):
        return "next"
    if action in ("quitter", "quit", "exit"):
        return "quit"
    if action in ("aide", "help"):
        render_help()
        return None
    if action in ("portefeuille", "portfolio"):
        return "show_portfolio"
    if action in ("acheter", "buy") and len(parts) == 3:
        ticker, qty = parts[1].upper(), parts[2]
        if not qty.isdigit():
            render_feedback(False, "Quantite invalide.")
            return None
        render_feedback(*player.buy(market, ticker, int(qty)))
        return None
    if action in ("vendre", "sell") and len(parts) == 3:
        ticker, qty = parts[1].upper(), parts[2]
        if not qty.isdigit():
            render_feedback(False, "Quantite invalide.")
            return None
        render_feedback(*player.sell(market, ticker, int(qty)))
        return None
    if action == "stop" and len(parts) == 3:
        ticker = parts[1].upper()
        try:
            price = float(parts[2])
        except ValueError:
            render_feedback(False, "Prix invalide.")
            return None
        if ticker not in player.holdings:
            render_feedback(False, f"Vous ne possedez pas {ticker}, impossible de poser un stop-loss.")
            return None
        player.stop_orders[ticker] = price
        render_feedback(True, f"Stop-loss pose sur {ticker} a {money(price)}.")
        return None
    if action == "annulerstop" and len(parts) == 2:
        ticker = parts[1].upper()
        if player.stop_orders.pop(ticker, None) is not None:
            render_feedback(True, f"Stop-loss annule sur {ticker}.")
        else:
            render_feedback(False, f"Aucun stop-loss actif sur {ticker}.")
        return None
    if action == "info" and len(parts) == 2:
        ticker = parts[1].upper()
        if ticker not in market:
            render_feedback(False, f"Ticker inconnu : {ticker}")
            return None
        render_info(market[ticker])
        return None

    render_feedback(False, "Commande non reconnue. Tapez 'aide' pour la liste des commandes.")
    return None


def render_summary(player: Player, market: dict[str, Stock], starting_capital: float) -> None:
    final_value = player.net_worth(market)
    total_return = (final_value - starting_capital) / starting_capital * 100
    style = pct_style(total_return)

    header = Text.assemble(
        ("Capital de depart : ", "bold white"), (f"{money(starting_capital)}\n", "white"),
        ("Valeur finale     : ", "bold white"), (f"{money(final_value)}\n", "white"),
        ("Performance       : ", "bold white"),
        (f"{pct_arrow(total_return)} {total_return:+.2f}%", f"bold {style}"),
    )

    if player.net_worth_history:
        curve = " ".join(f"{v:,.0f}" for v in player.net_worth_history[-10:])
        header.append(f"\nEvolution (10 derniers jours) : [{curve}]", style=NEUTRAL)

    lessons = Table.grid(padding=(0, 1))
    lessons.add_column()

    if len(player.tickers_ever_held) == 0:
        lessons.add_row("• Vous n'avez rien achete : impossible de faire fructifier un capital laisse en cash.")
    elif len(player.tickers_ever_held) == 1:
        lessons.add_row("• Vous avez surtout mise sur une seule action : la diversification reduit le risque.")
    else:
        lessons.add_row(f"• Vous avez diversifie sur {len(player.tickers_ever_held)} actions differentes, bravo.")

    if player.used_stop_loss:
        lessons.add_row("• Vous avez utilise un stop-loss : ce reflexe protege un vrai portefeuille des grosses pertes.")
    else:
        lessons.add_row("• Vous n'avez jamais utilise de stop-loss, ce qui expose a des pertes plus importantes.")

    if total_return < 0:
        lessons.add_row("• Performance negative : frequent, meme chez des traders experimentes. On apprend en jouant.")
    elif total_return == 0:
        lessons.add_row("• Performance neutre : essayez de prendre plus (ou moins) de risques la prochaine fois.")
    else:
        lessons.add_row("• Performance positive : une seule partie gagnante ne prouve pas qu'une strategie est fiable.")

    console.print(
        Panel(
            Text.assemble(header, "\n\n", Text("Lecons de cette partie :\n", style=f"bold {ACCENT}")),
            title=f"[bold {style}]◆ FIN DE PARTIE - BILAN ◆[/bold {style}]",
            border_style=style,
            box=HEAVY,
        )
    )
    console.print(lessons)
    console.print(
        "\n[dim italic]Rappel : ceci est une simulation. Les vrais marches financiers "
        "comportent un risque reel de perte en capital.[/dim italic]\n"
    )


def play(days: int, starting_capital: float, seed: int | None) -> None:
    market = build_market(seed)
    player = Player(cash=starting_capital)

    render_banner(days, starting_capital)
    render_help()

    for day in range(1, days + 1):
        previous_prices = {t: s.price for t, s in market.items()}

        if day > 1:
            for stock in market.values():
                stock.step()
            headline = maybe_trigger_news(market)
            if headline:
                render_news(headline)

        stop_messages = player.check_stop_orders(market)
        if stop_messages:
            render_stop_loss_messages(stop_messages)

        render_day_header(day, days)
        render_market(market, previous_prices)
        render_portfolio(player, market, starting_capital)

        while True:
            try:
                command = Prompt.ask(f"[bold {ACCENT}]➤[/bold {ACCENT}]")
            except EOFError:
                command = "quitter"
            result = handle_command(command, player, market)
            if result == "show_portfolio":
                render_portfolio(player, market, starting_capital)
                continue
            if result == "next":
                break
            if result == "quit":
                player.net_worth_history.append(player.net_worth(market))
                render_summary(player, market, starting_capital)
                return

        player.net_worth_history.append(player.net_worth(market))

    render_summary(player, market, starting_capital)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jeu pedagogique de trading (marche fictif).")
    parser.add_argument("--days", type=int, default=20, help="Nombre de jours de bourse (defaut: 20).")
    parser.add_argument("--capital", type=float, default=10000.0, help="Capital de depart en EUR (defaut: 10000).")
    parser.add_argument("--seed", type=int, default=None, help="Graine aleatoire pour rejouer la meme partie.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.days < 1:
        raise SystemExit("Le nombre de jours doit etre superieur ou egal a 1.")
    if args.capital <= 0:
        raise SystemExit("Le capital de depart doit etre positif.")
    try:
        play(args.days, args.capital, args.seed)
    except KeyboardInterrupt:
        console.print("\n[dim]Partie interrompue.[/dim]")


if __name__ == "__main__":
    main()
