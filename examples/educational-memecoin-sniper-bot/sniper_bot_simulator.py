#!/usr/bin/env python3
"""
Simulateur pedagogique d'un bot "intelligent" de sniping de meme coins.

But: coder un VRAI bot avec une VRAIE logique de detection de risque
(comme le ferait un bot professionnel : verification de la liquidite
verrouillee, de la repartition des holders, des "bundlers", etc.),
mais applique sur un marche 100% simule. Aucune connexion a un vrai
wallet, aucun vrai token, aucun argent reel.

Pourquoi un marche simule et pas un vrai bot connecte a Axiom/Solana ?
    Parce qu'un vrai bot de sniping de meme coins, avec de l'argent
    reel, mise sur un marche ou environ 98% des tokens s'effondrent
    (donnees on-chain reelles de Pump.fun, mars 2026). Ce simulateur
    permet de coder et tester la MEME logique de detection, en toute
    securite, et de voir statistiquement si "etre intelligent" change
    vraiment la donne (spoiler : ca reduit le risque d'arnaque
    grossiere, mais ca ne permet PAS de predire les "moonshots").

Le bot simule deux strategies sur le MEME flux de nouveaux tokens,
pour comparaison directe :
    1. "Bot intelligent"   : n'achete que si les criteres de securite
                             sont respectes (liquidite verrouillee,
                             faible concentration des holders, etc.)
    2. "Achat aveugle"      : achete systematiquement 1 SOL sur CHAQUE
                             nouveau token, sans aucun filtre (le
                             comportement d'un debutant qui clique
                             sur tout ce qu'il voit).

Usage:
    python3 sniper_bot_simulator.py
    python3 sniper_bot_simulator.py --launches 1000 --trade-size 1 --seed 42
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass, field
from enum import Enum


class Outcome(Enum):
    RUG_INSTANT = "rug_instant"
    SLOW_BLEED = "slow_bleed"
    STABLE = "stable"
    MOONSHOT = "moonshot"


@dataclass
class LaunchedToken:
    id: int
    name: str
    lp_locked: bool
    dev_holding_pct: float
    top10_holder_pct: float
    bundler_pct: float
    sniper_pct: float
    risk_score: float = field(init=False)

    def __post_init__(self) -> None:
        # Score de risque compose (0 = tres sain, 1 = tres suspect).
        # Chaque "red flag" contribue proportionnellement au risque.
        lp_risk = 0.0 if self.lp_locked else 0.35
        dev_risk = min(self.dev_holding_pct / 40.0, 1.0) * 0.25
        top10_risk = min(self.top10_holder_pct / 60.0, 1.0) * 0.25
        bundler_risk = min(self.bundler_pct / 20.0, 1.0) * 0.15
        self.risk_score = min(lp_risk + dev_risk + top10_risk + bundler_risk, 1.0)


ADJECTIVES = ["Moon", "Turbo", "Based", "Giga", "Rocket", "Lucky", "Diamond", "Rug", "Chad", "Sigma"]
NOUNS = ["Doge", "Cat", "Frog", "Inu", "Pepe", "Coin", "Chad", "Wojak", "Banana", "Elon"]


def generate_token(token_id: int, rng: random.Random) -> LaunchedToken:
    name = f"{rng.choice(ADJECTIVES)}{rng.choice(NOUNS)}{token_id}"
    return LaunchedToken(
        id=token_id,
        name=name,
        lp_locked=rng.random() < 0.55,
        dev_holding_pct=rng.uniform(0, 45),
        top10_holder_pct=rng.uniform(5, 70),
        bundler_pct=rng.uniform(0, 20),
        sniper_pct=rng.uniform(0, 20),
    )


@dataclass
class FilterConfig:
    require_lp_locked: bool = True
    max_dev_holding_pct: float = 15.0
    max_top10_holder_pct: float = 35.0
    max_bundler_pct: float = 10.0

    def passes(self, token: LaunchedToken) -> bool:
        if self.require_lp_locked and not token.lp_locked:
            return False
        if token.dev_holding_pct > self.max_dev_holding_pct:
            return False
        if token.top10_holder_pct > self.max_top10_holder_pct:
            return False
        if token.bundler_pct > self.max_bundler_pct:
            return False
        return True


def resolve_outcome(token: LaunchedToken, rng: random.Random) -> tuple[Outcome, float]:
    """
    Determine ce qui arrive au token apres l'achat.

    Le risque visible (LP, holders, bundlers) influence fortement la
    probabilite d'un rug pull immediat. En revanche, la probabilite
    d'un "moonshot" reste volontairement quasi independante du score
    de risque : la viralite est fondamentalement imprevisible, un bot
    ne peut pas la detecter a l'avance, meme s'il est "intelligent".
    """
    risk = token.risk_score

    p_rug_instant = min(0.15 + 0.70 * risk, 0.92)
    p_moonshot = max(0.020 - 0.010 * risk, 0.005)
    p_stable = max(0.06 - 0.03 * risk, 0.02)
    p_slow_bleed = max(1.0 - p_rug_instant - p_moonshot - p_stable, 0.0)

    roll = rng.random()
    cumulative = 0.0
    for outcome, probability in (
        (Outcome.RUG_INSTANT, p_rug_instant),
        (Outcome.SLOW_BLEED, p_slow_bleed),
        (Outcome.STABLE, p_stable),
        (Outcome.MOONSHOT, p_moonshot),
    ):
        cumulative += probability
        if roll <= cumulative:
            chosen = outcome
            break
    else:
        chosen = Outcome.SLOW_BLEED

    if chosen is Outcome.RUG_INSTANT:
        multiplier = rng.uniform(0.0, 0.05)
    elif chosen is Outcome.SLOW_BLEED:
        multiplier = rng.uniform(0.10, 0.55)
    elif chosen is Outcome.STABLE:
        multiplier = rng.uniform(0.80, 1.35)
    else:  # MOONSHOT
        # La plupart des "moonshots" font x2-x10, une infime minorite fait bien plus.
        multiplier = rng.uniform(2.0, 10.0) if rng.random() > 0.05 else rng.uniform(10.0, 60.0)

    return chosen, multiplier


@dataclass
class StrategyResult:
    name: str
    trades: int = 0
    total_invested_sol: float = 0.0
    total_returned_sol: float = 0.0
    wins: int = 0
    rugs: int = 0
    best_multiplier: float = 0.0
    worst_multiplier: float = float("inf")
    outcome_counts: dict[Outcome, int] = field(default_factory=lambda: {o: 0 for o in Outcome})

    def record_trade(self, multiplier: float, outcome: Outcome, trade_size: float, fee_rate: float) -> None:
        self.trades += 1
        self.total_invested_sol += trade_size
        returned = trade_size * multiplier * (1 - fee_rate)
        self.total_returned_sol += returned
        self.outcome_counts[outcome] += 1
        if multiplier >= 1.0:
            self.wins += 1
        if outcome is Outcome.RUG_INSTANT:
            self.rugs += 1
        self.best_multiplier = max(self.best_multiplier, multiplier)
        self.worst_multiplier = min(self.worst_multiplier, multiplier)

    def print_summary(self) -> None:
        pnl = self.total_returned_sol - self.total_invested_sol
        roi_pct = (pnl / self.total_invested_sol * 100) if self.total_invested_sol > 0 else 0.0
        win_rate = (self.wins / self.trades * 100) if self.trades else 0.0
        rug_rate = (self.rugs / self.trades * 100) if self.trades else 0.0

        print(f"\n=== {self.name} ===")
        print(f"  Trades effectues        : {self.trades}")
        print(f"  SOL investi au total    : {self.total_invested_sol:.2f} SOL")
        print(f"  SOL recupere au total   : {self.total_returned_sol:.2f} SOL")
        print(f"  Resultat net (P&L)      : {pnl:+.2f} SOL ({roi_pct:+.1f}%)")
        print(f"  Taux de 'reussite' (>=1x): {win_rate:.1f}%")
        print(f"  Taux de rug pull instant: {rug_rate:.1f}%")
        print(f"  Meilleur multiplicateur : x{self.best_multiplier:.2f}")
        print(f"  Pire multiplicateur     : x{self.worst_multiplier:.3f}")
        print("  Repartition des issues  :")
        for outcome in Outcome:
            count = self.outcome_counts[outcome]
            pct = (count / self.trades * 100) if self.trades else 0.0
            print(f"    - {outcome.value:<12}: {count:>5} ({pct:5.1f}%)")


def run_simulation(num_launches: int, trade_size: float, fee_rate: float, seed: int | None) -> None:
    rng = random.Random(seed)

    smart_config = FilterConfig()
    smart_bot = StrategyResult(name="Bot intelligent (avec filtre de securite)")
    blind_bot = StrategyResult(name="Achat aveugle (aucun filtre, comme un debutant)")

    filtered_count = 0

    for i in range(1, num_launches + 1):
        token = generate_token(i, rng)
        outcome, multiplier = resolve_outcome(token, rng)

        # L'achat aveugle achete TOUJOURS.
        blind_bot.record_trade(multiplier, outcome, trade_size, fee_rate)

        # Le bot intelligent n'achete que si le token passe le filtre.
        if smart_config.passes(token):
            filtered_count += 1
            smart_bot.record_trade(multiplier, outcome, trade_size, fee_rate)

    print("=== Simulateur de bot de sniping de meme coins (marche simule) ===")
    print(f"Nombre de nouveaux tokens generes : {num_launches}")
    print(f"Taille de position (par trade)    : {trade_size} SOL")
    print(f"Tokens ayant passe le filtre       : {filtered_count} ({filtered_count / num_launches * 100:.1f}%)")

    blind_bot.print_summary()
    smart_bot.print_summary()

    print("\n=== Comparaison ===")
    blind_pnl = blind_bot.total_returned_sol - blind_bot.total_invested_sol
    smart_pnl = smart_bot.total_returned_sol - smart_bot.total_invested_sol
    print(f"P&L achat aveugle   : {blind_pnl:+.2f} SOL")
    print(f"P&L bot intelligent : {smart_pnl:+.2f} SOL")
    print(f"Taux de rug pull instant -> aveugle: {blind_bot.rugs / blind_bot.trades * 100:.1f}%"
          f" vs intelligent: {smart_bot.rugs / smart_bot.trades * 100:.1f}%")
    print(
        "\nCe que ça montre généralement : le filtre intelligent réduit nettement le\n"
        "taux de rug pull instantané (il évite les arnaques les plus grossières),\n"
        "MAIS il ne change presque rien à la probabilité de tomber sur un vrai\n"
        "'moonshot' — parce que la viralité d'un meme coin est fondamentalement\n"
        "imprévisible, même pour un bot très sophistiqué. Dans les deux cas, sur un\n"
        "grand nombre d'essais, le résultat net a de fortes chances d'être négatif."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulateur pedagogique d'un bot intelligent de sniping de meme coins."
    )
    parser.add_argument("--launches", type=int, default=500, help="Nombre de nouveaux tokens a simuler (defaut: 500).")
    parser.add_argument("--trade-size", type=float, default=1.0, help="Taille de position en SOL par trade (defaut: 1.0).")
    parser.add_argument("--fee-rate", type=float, default=0.02, help="Frais de swap cumules par trade, ex: 0.02 = 2%% (defaut: 0.02).")
    parser.add_argument("--seed", type=int, default=None, help="Graine aleatoire pour reproduire exactement la meme simulation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.launches < 1:
        raise SystemExit("Le nombre de lancements doit etre superieur ou egal a 1.")
    if args.trade_size <= 0:
        raise SystemExit("La taille de position doit etre positive.")
    run_simulation(args.launches, args.trade_size, args.fee_rate, args.seed)


if __name__ == "__main__":
    main()
