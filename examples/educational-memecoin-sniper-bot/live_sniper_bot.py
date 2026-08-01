#!/usr/bin/env python3
"""
ZACHXBTBOT - Simulateur de bot de sniping "en direct" (marche 100% fictif).

Recree l'experience complete d'un bot de sniping reel :
    1. Tu tapes "start".
    2. Le bot "surveille" en continu l'arrivee de nouveaux tokens.
    3. Des qu'un token "vient d'etre lance", il affiche une alerte avec
       un lien FICTIF (jamais un vrai lien Axiom/Solana).
    4. Le bot decide, selon ses regles de securite, d'investir 1 SOL
       (fictif) ou d'ignorer le token.
    5. Si il achete, il "regarde" le prix evoluer en temps reel, puis
       revend automatiquement, et affiche le resultat.
    6. Un portefeuille virtuel cumule les resultats au fil du temps.

AUCUNE connexion reelle : ni a Axiom, ni a Solana, ni a un vrai wallet.
Tous les tokens, liens et prix sont generes aleatoirement pour
reproduire l'EXPERIENCE d'un bot de sniping, sans jamais risquer un
centime reel. C'est fait pour comprendre, par la pratique, a quel point
ce type de trading est rapide, imprevisible, et defavorable sur le long
terme (voir les statistiques dans le README).

Usage:
    python3 live_sniper_bot.py
    python3 live_sniper_bot.py --max-launches 20 --seed 42
    python3 live_sniper_bot.py --fast   (enchaine les lancements plus vite)
"""

from __future__ import annotations

import argparse
import random
import time
import uuid

from sniper_bot_simulator import FilterConfig, generate_token, resolve_outcome, Outcome


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{Colors.RESET}"


def fake_link(rng: random.Random) -> str:
    fake_hash = uuid.UUID(int=rng.getrandbits(128)).hex[:34]
    return f"[SIMULATION] axiom.SIMULE/meme/{fake_hash}?chain=sol"


def print_banner() -> None:
    print(colorize("=" * 64, Colors.MAGENTA))
    print(colorize("  ZACHXBTBOT — Simulateur de bot de sniping (marche fictif)", Colors.BOLD + Colors.MAGENTA))
    print(colorize("=" * 64, Colors.MAGENTA))
    print(
        "Ce bot ne se connecte a AUCUN vrai wallet et n'utilise AUCUN\n"
        "argent reel. Tous les tokens et liens sont fictifs, generes\n"
        "aleatoirement, pour simuler l'experience d'un vrai bot de sniping."
    )
    print()


def print_alert(token, link: str, seconds_ago: int) -> None:
    print(colorize(f"\n🆕 NOUVEAU TOKEN DETECTE (il y a {seconds_ago}s)", Colors.YELLOW + Colors.BOLD))
    print(f"   Nom            : {token.name}")
    print(f"   Lien           : {colorize(link, Colors.CYAN)}")
    print(f"   LP verrouillee : {'Oui' if token.lp_locked else 'NON'}")
    print(f"   Dev holding    : {token.dev_holding_pct:.1f}%")
    print(f"   Top 10 holders : {token.top10_holder_pct:.1f}%")
    print(f"   Bundlers       : {token.bundler_pct:.1f}%")
    print(f"   Score de risque: {token.risk_score:.2f} / 1.00")


def simulate_price_path(final_multiplier: float, rng: random.Random, steps: int = 5) -> list[float]:
    path = []
    for i in range(1, steps + 1):
        progress = i / steps
        noise = rng.uniform(-0.20, 0.20) * max(final_multiplier, 1.0)
        value = max(1.0 + (final_multiplier - 1.0) * progress + noise, 0.0)
        path.append(value)
    path[-1] = final_multiplier
    return path


def run_live_bot(max_launches: int, trade_size: float, fee_rate: float, seed: int | None, fast: bool) -> None:
    rng = random.Random(seed)
    filter_config = FilterConfig()

    portfolio_sol = 0.0
    invested_sol = 0.0
    trades = 0
    wins = 0
    rugs = 0

    print_banner()
    try:
        input(colorize("Tape ENTREE pour lancer la surveillance (Ctrl+C pour arreter a tout moment)...\n", Colors.DIM))
    except (EOFError, KeyboardInterrupt):
        print("\nArret.")
        return

    print(colorize("🔍 Surveillance des nouveaux lancements en cours...\n", Colors.CYAN))

    launch_wait = (0.3, 0.8) if fast else (1.0, 2.5)
    tick_delay = 0.08 if fast else 0.25

    launch_id = 0
    try:
        while max_launches == 0 or launch_id < max_launches:
            launch_id += 1
            time.sleep(rng.uniform(*launch_wait))

            token = generate_token(launch_id, rng)
            link = fake_link(rng)
            seconds_ago = rng.randint(1, 5)
            print_alert(token, link, seconds_ago)

            if not filter_config.passes(token):
                print(colorize("   ⏭️  IGNORE : ne passe pas le filtre de securite (trop risque).", Colors.DIM))
                continue

            print(colorize(f"   ✅ ACHAT : {trade_size} SOL investi dans {token.name}", Colors.GREEN + Colors.BOLD))
            trades += 1
            invested_sol += trade_size

            outcome, final_multiplier = resolve_outcome(token, rng)
            path = simulate_price_path(final_multiplier, rng)

            print("   📈 Suivi du prix : ", end="", flush=True)
            for value in path:
                color = Colors.GREEN if value >= 1.0 else Colors.RED
                print(colorize(f"x{value:.2f} ", color), end="", flush=True)
                time.sleep(tick_delay)
            print()

            returned = trade_size * final_multiplier * (1 - fee_rate)
            pnl = returned - trade_size
            portfolio_sol += pnl

            if outcome is Outcome.RUG_INSTANT:
                rugs += 1
            if final_multiplier >= 1.0:
                wins += 1

            result_color = Colors.GREEN if pnl >= 0 else Colors.RED
            result_label = "RUG PULL !" if outcome is Outcome.RUG_INSTANT else "Vente automatique"
            print(
                colorize(
                    f"   💰 {result_label} -> x{final_multiplier:.2f} "
                    f"({pnl:+.3f} SOL) | Portefeuille cumule : {portfolio_sol:+.3f} SOL",
                    result_color,
                )
            )

    except KeyboardInterrupt:
        print(colorize("\n\nArret manuel du bot.", Colors.YELLOW))

    print(colorize("\n" + "=" * 64, Colors.MAGENTA))
    print(colorize("  BILAN DE LA SESSION", Colors.BOLD + Colors.MAGENTA))
    print(colorize("=" * 64, Colors.MAGENTA))
    print(f"  Tokens observes        : {launch_id}")
    print(f"  Trades executes        : {trades}")
    print(f"  SOL investi (fictif)   : {invested_sol:.3f} SOL")
    print(f"  Resultat net (P&L)     : {portfolio_sol:+.3f} SOL")
    if trades:
        print(f"  Taux de reussite (>=1x): {wins / trades * 100:.1f}%")
        print(f"  Taux de rug pull       : {rugs / trades * 100:.1f}%")
    print(
        "\nRappel : cette session est 100% simulee. Sur le vrai marche, ces\n"
        "resultats correspondent aux vraies statistiques observees sur\n"
        "Pump.fun (~96% des participants finissent en perte ou avec un\n"
        "gain negligeable sur un mois donne)."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ZACHXBTBOT - bot de sniping de meme coins en direct (simulation).")
    parser.add_argument("--max-launches", type=int, default=15, help="Nombre de lancements a observer (0 = infini, defaut: 15).")
    parser.add_argument("--trade-size", type=float, default=1.0, help="Taille de position en SOL (defaut: 1.0).")
    parser.add_argument("--fee-rate", type=float, default=0.02, help="Frais de swap cumules (defaut: 0.02 = 2%%).")
    parser.add_argument("--seed", type=int, default=None, help="Graine aleatoire pour rejouer la meme session.")
    parser.add_argument("--fast", action="store_true", help="Enchaine les lancements plus rapidement.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_launches < 0:
        raise SystemExit("--max-launches doit etre >= 0.")
    if args.trade_size <= 0:
        raise SystemExit("--trade-size doit etre positif.")
    run_live_bot(args.max_launches, args.trade_size, args.fee_rate, args.seed, args.fast)


if __name__ == "__main__":
    main()
