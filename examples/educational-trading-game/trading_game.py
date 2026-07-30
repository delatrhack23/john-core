#!/usr/bin/env python3
"""
Jeu pedagogique de trading en bourse (marche fictif).

But: apprendre les bases du trading (achat/vente, gestion du risque,
stop-loss, diversification) SANS RISQUER D'ARGENT REEL. Aucune connexion
a un vrai broker, aucune vraie donnee de marche: tout est simule.

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


SPARK_CHARS = "▁▂▃▄▅▆▇█"


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

    def buy(self, market: dict[str, Stock], ticker: str, qty: int) -> str:
        if ticker not in market:
            return f"Ticker inconnu: {ticker}"
        if qty <= 0:
            return "Quantite invalide."
        cost = market[ticker].price * qty
        if cost > self.cash:
            return f"Fonds insuffisants (cout {cost:.2f} EUR, cash disponible {self.cash:.2f} EUR)."
        self.cash -= cost
        self.holdings[ticker] = self.holdings.get(ticker, 0) + qty
        self.tickers_ever_held.add(ticker)
        return f"Achete {qty} x {ticker} a {market[ticker].price:.2f} EUR (total {cost:.2f} EUR)."

    def sell(self, market: dict[str, Stock], ticker: str, qty: int) -> str:
        if ticker not in market:
            return f"Ticker inconnu: {ticker}"
        held = self.holdings.get(ticker, 0)
        if qty <= 0:
            return "Quantite invalide."
        if qty > held:
            return f"Vous ne possedez que {held} x {ticker}."
        revenue = market[ticker].price * qty
        self.cash += revenue
        self.holdings[ticker] -= qty
        if self.holdings[ticker] == 0:
            del self.holdings[ticker]
            self.stop_orders.pop(ticker, None)
        return f"Vendu {qty} x {ticker} a {market[ticker].price:.2f} EUR (total {revenue:.2f} EUR)."

    def check_stop_orders(self, market: dict[str, Stock]) -> list[str]:
        messages = []
        for ticker in list(self.stop_orders.keys()):
            threshold = self.stop_orders[ticker]
            if ticker in self.holdings and market[ticker].price <= threshold:
                qty = self.holdings[ticker]
                msg = self.sell(market, ticker, qty)
                self.used_stop_loss = True
                messages.append(
                    f"STOP-LOSS declenche sur {ticker} (seuil {threshold:.2f} EUR) -> {msg}"
                )
        return messages


def print_header(day: int, total_days: int) -> None:
    print("\n" + "=" * 60)
    print(f" JOUR {day}/{total_days}")
    print("=" * 60)


def print_market(market: dict[str, Stock], previous_prices: dict[str, float]) -> None:
    print(f"{'Ticker':<8}{'Nom':<16}{'Secteur':<14}{'Prix (EUR)':>12}{'Var.':>10}")
    for ticker, stock in market.items():
        prev = previous_prices.get(ticker, stock.price)
        change_pct = (stock.price - prev) / prev * 100 if prev else 0.0
        change_txt = f"{change_pct:+.2f}%"
        print(
            f"{ticker:<8}{stock.name:<16}{stock.sector:<14}"
            f"{stock.price:>12.2f}{change_txt:>10}"
        )


def print_portfolio(player: Player, market: dict[str, Stock]) -> None:
    print(f"\nCash disponible : {player.cash:.2f} EUR")
    if not player.holdings:
        print("Positions        : aucune")
    else:
        print("Positions:")
        for ticker, qty in player.holdings.items():
            value = qty * market[ticker].price
            stop = player.stop_orders.get(ticker)
            stop_txt = f", stop-loss a {stop:.2f} EUR" if stop else ""
            print(f"  {ticker}: {qty} actions -> {value:.2f} EUR{stop_txt}")
    print(f"Valeur totale du portefeuille : {player.net_worth(market):.2f} EUR")


def print_help() -> None:
    print(
        "\nCommandes disponibles :\n"
        "  acheter TICKER QTE    (ou: buy)      -- acheter des actions\n"
        "  vendre TICKER QTE     (ou: sell)      -- vendre des actions\n"
        "  stop TICKER PRIX                      -- poser un stop-loss\n"
        "  annulerstop TICKER                    -- annuler un stop-loss\n"
        "  info TICKER                           -- details sur une action\n"
        "  portefeuille          (ou: portfolio) -- voir son portefeuille\n"
        "  aide                  (ou: help)      -- afficher cette aide\n"
        "  suivant               (ou: next)      -- passer au jour suivant\n"
        "  quitter               (ou: quit)      -- terminer la partie\n"
    )


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
        print_help()
        return None
    if action in ("portefeuille", "portfolio"):
        print_portfolio(player, market)
        return None
    if action in ("acheter", "buy") and len(parts) == 3:
        ticker, qty = parts[1].upper(), parts[2]
        if not qty.isdigit():
            print("Quantite invalide.")
            return None
        print(player.buy(market, ticker, int(qty)))
        return None
    if action in ("vendre", "sell") and len(parts) == 3:
        ticker, qty = parts[1].upper(), parts[2]
        if not qty.isdigit():
            print("Quantite invalide.")
            return None
        print(player.sell(market, ticker, int(qty)))
        return None
    if action == "stop" and len(parts) == 3:
        ticker = parts[1].upper()
        try:
            price = float(parts[2])
        except ValueError:
            print("Prix invalide.")
            return None
        if ticker not in player.holdings:
            print(f"Vous ne possedez pas {ticker}, impossible de poser un stop-loss.")
            return None
        player.stop_orders[ticker] = price
        print(f"Stop-loss pose sur {ticker} a {price:.2f} EUR.")
        return None
    if action == "annulerstop" and len(parts) == 2:
        ticker = parts[1].upper()
        if player.stop_orders.pop(ticker, None) is not None:
            print(f"Stop-loss annule sur {ticker}.")
        else:
            print(f"Aucun stop-loss actif sur {ticker}.")
        return None
    if action == "info" and len(parts) == 2:
        ticker = parts[1].upper()
        if ticker not in market:
            print(f"Ticker inconnu: {ticker}")
            return None
        stock = market[ticker]
        print(
            f"\n{stock.name} ({ticker}) - Secteur: {stock.sector}\n"
            f"  Prix actuel     : {stock.price:.2f} EUR\n"
            f"  Volatilite      : {stock.volatility_label()}\n"
            f"  Historique      : {stock.sparkline()}\n"
        )
        return None

    print("Commande non reconnue. Tapez 'aide' pour la liste des commandes.")
    return None


def print_summary(player: Player, market: dict[str, Stock], starting_capital: float) -> None:
    final_value = player.net_worth(market)
    total_return = (final_value - starting_capital) / starting_capital * 100

    print("\n" + "#" * 60)
    print("  FIN DE PARTIE - BILAN")
    print("#" * 60)
    print(f"Capital de depart      : {starting_capital:.2f} EUR")
    print(f"Valeur finale           : {final_value:.2f} EUR")
    print(f"Performance totale      : {total_return:+.2f} %")

    if player.net_worth_history:
        print(f"Evolution du capital    : {'[' + ' '.join(f'{v:.0f}' for v in player.net_worth_history[-10:]) + ']'}")

    print("\nLecons de cette partie :")
    if len(player.tickers_ever_held) == 0:
        print("  - Vous n'avez rien achete : impossible de faire fructifier un capital")
        print("    en le laissant simplement en cash (mais aussi impossible de le perdre !).")
    elif len(player.tickers_ever_held) == 1:
        print("  - Vous avez surtout mise sur une seule action : rappelez-vous que la")
        print("    diversification reduit le risque de tout perdre sur un seul pari.")
    else:
        print(f"  - Vous avez diversifie sur {len(player.tickers_ever_held)} actions differentes, bravo.")

    if player.used_stop_loss:
        print("  - Vous avez utilise un stop-loss : c'est exactement le reflexe qui")
        print("    protege un vrai portefeuille contre les grosses pertes.")
    else:
        print("  - Vous n'avez jamais utilise de stop-loss. Sur un vrai marche, cela")
        print("    peut transformer une petite perte en perte catastrophique.")

    if total_return < 0:
        print("  - Performance negative : c'est normal et frequent, meme pour des")
        print("    traders experimentes. L'important est d'apprendre de chaque partie.")
    elif total_return == 0:
        print("  - Performance neutre : vous n'avez ni gagne ni perdu, essayez de")
        print("    prendre plus (ou moins) de risques pour voir l'effet sur le resultat.")
    else:
        print("  - Performance positive : attention cependant, une seule partie gagnante")
        print("    ne prouve pas qu'une strategie est fiable sur le long terme.")

    print("\nRappel : ceci est une simulation. Les vrais marches financiers")
    print("comportent un risque reel de perte en capital.")


def play(days: int, starting_capital: float, seed: int | None) -> None:
    market = build_market(seed)
    player = Player(cash=starting_capital)

    print("=== Jeu pedagogique de trading (marche 100% fictif) ===")
    print(f"Capital de depart : {starting_capital:.2f} EUR sur {days} jours de bourse.")
    print_help()

    for day in range(1, days + 1):
        previous_prices = {t: s.price for t, s in market.items()}

        if day > 1:
            for stock in market.values():
                stock.step()
            headline = maybe_trigger_news(market)
            if headline:
                print(f"\n[ACTUALITE] {headline}")

        for message in player.check_stop_orders(market):
            print(message)

        print_header(day, days)
        print_market(market, previous_prices)
        print_portfolio(player, market)

        while True:
            try:
                command = input("\n> ")
            except EOFError:
                command = "quitter"
            result = handle_command(command, player, market)
            if result == "next":
                break
            if result == "quit":
                player.net_worth_history.append(player.net_worth(market))
                print_summary(player, market, starting_capital)
                return

        player.net_worth_history.append(player.net_worth(market))

    print_summary(player, market, starting_capital)


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
        print("\nPartie interrompue.")


if __name__ == "__main__":
    main()
