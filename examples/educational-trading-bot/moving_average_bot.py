#!/usr/bin/env python3
"""
Bot de trading pedagogique - strategie de croisement de moyennes mobiles
(Moving Average Crossover), execute en BACKTEST (sur des donnees passees).

Ce script n'envoie AUCUN ordre reel a un broker ou un exchange. Il simule
ce qu'aurait fait une strategie automatisee sur des donnees historiques
(reelles ou synthetiques), pour comprendre comment un bot de trading est
concu et evalue AVANT de risquer un centime.

Principe de la strategie:
    - On calcule deux moyennes mobiles du prix: une "courte" (reactive)
      et une "longue" (plus lissee).
    - Quand la moyenne courte croise AU-DESSUS de la moyenne longue,
      c'est un signal d'ACHAT (tendance haussiere naissante).
    - Quand la moyenne courte croise EN-DESSOUS de la moyenne longue,
      c'est un signal de VENTE (tendance baissiere naissante).
    - On compare le resultat avec une strategie "buy & hold" (acheter
      et ne plus toucher) pour voir si la strategie apporte une reelle
      valeur ajoutee.

Sources de donnees disponibles (--source):
    synthetic   Donnees generees aleatoirement, aucune dependance,
                aucun acces reseau necessaire (par defaut).
    csv         Fichier CSV local avec deux colonnes "date,close".
    yfinance    Vraies donnees historiques telechargees via la
                bibliotheque "yfinance" (necessite une connexion
                internet et `pip install yfinance`).

Exemples:
    python3 moving_average_bot.py
    python3 moving_average_bot.py --source synthetic --days 250 --seed 1
    python3 moving_average_bot.py --source csv --csv-path mes_prix.csv
    python3 moving_average_bot.py --source yfinance --ticker AAPL --period 1y

AVERTISSEMENT: un backtest gagnant ne garantit absolument pas des gains
futurs. Les marches reels comportent un risque reel de perte en capital.
"""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass, field


SPARK_CHARS = "▁▂▃▄▅▆▇█"


@dataclass
class PricePoint:
    date: str
    close: float


def load_synthetic(days: int, seed: int | None, start_price: float = 100.0) -> list[PricePoint]:
    """Genere une serie de prix fictive (marche aleatoire avec tendance)."""
    if seed is not None:
        random.seed(seed)
    price = start_price
    points: list[PricePoint] = []
    for day in range(days):
        if day > 0:
            price = max(0.5, price * (1 + random.gauss(0.0006, 0.018)))
        points.append(PricePoint(date=f"J+{day}", close=round(price, 2)))
    return points


def load_csv(path: str) -> list[PricePoint]:
    """Charge un CSV avec des colonnes 'date' et 'close' (ou 'price')."""
    points: list[PricePoint] = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [f.lower() for f in (reader.fieldnames or [])]
        if "date" not in fieldnames:
            raise SystemExit("Le fichier CSV doit contenir une colonne 'date'.")
        price_field = "close" if "close" in fieldnames else "price" if "price" in fieldnames else None
        if price_field is None:
            raise SystemExit("Le fichier CSV doit contenir une colonne 'close' ou 'price'.")
        original_fields = {f.lower(): f for f in reader.fieldnames or []}
        for row in reader:
            date = row[original_fields["date"]]
            close = float(row[original_fields[price_field]])
            points.append(PricePoint(date=date, close=close))
    if len(points) < 2:
        raise SystemExit("Le fichier CSV doit contenir au moins 2 lignes de donnees.")
    return points


def load_yfinance(ticker: str, period: str, interval: str) -> list[PricePoint]:
    """Telecharge de vraies donnees historiques via yfinance (optionnel)."""
    try:
        import yfinance as yf
    except ImportError as exc:
        raise SystemExit(
            "La bibliotheque 'yfinance' n'est pas installee.\n"
            "Installez-la avec: pip install yfinance"
        ) from exc

    data = yf.download(ticker, period=period, interval=interval, progress=False)
    if data.empty:
        raise SystemExit(f"Aucune donnee trouvee pour le ticker '{ticker}'.")

    close_col = data["Close"]
    points = [
        PricePoint(date=str(idx.date()) if hasattr(idx, "date") else str(idx), close=float(value))
        for idx, value in zip(data.index, close_col.squeeze().tolist())
    ]
    return points


def simple_moving_average(prices: list[float], window: int) -> list[float | None]:
    result: list[float | None] = []
    running_sum = 0.0
    for i, price in enumerate(prices):
        running_sum += price
        if i >= window:
            running_sum -= prices[i - window]
        result.append(running_sum / window if i >= window - 1 else None)
    return result


@dataclass
class Trade:
    date: str
    action: str  # "ACHAT" ou "VENTE"
    price: float
    shares: float


@dataclass
class BacktestResult:
    equity_curve: list[float] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    final_equity: float = 0.0
    buy_and_hold_final: float = 0.0
    max_drawdown_pct: float = 0.0


def run_backtest(
    points: list[PricePoint],
    short_window: int,
    long_window: int,
    starting_capital: float,
) -> BacktestResult:
    prices = [p.close for p in points]
    short_ma = simple_moving_average(prices, short_window)
    long_ma = simple_moving_average(prices, long_window)

    cash = starting_capital
    shares = 0.0
    result = BacktestResult()

    peak_equity = starting_capital

    for i in range(len(points)):
        price = prices[i]
        equity = cash + shares * price
        result.equity_curve.append(equity)
        peak_equity = max(peak_equity, equity)
        drawdown = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0.0
        result.max_drawdown_pct = max(result.max_drawdown_pct, drawdown)

        if i == 0 or short_ma[i] is None or long_ma[i] is None or short_ma[i - 1] is None or long_ma[i - 1] is None:
            continue

        crossed_up = short_ma[i - 1] <= long_ma[i - 1] and short_ma[i] > long_ma[i]
        crossed_down = short_ma[i - 1] >= long_ma[i - 1] and short_ma[i] < long_ma[i]

        if crossed_up and shares == 0.0 and cash > 0:
            shares = cash / price
            result.trades.append(Trade(points[i].date, "ACHAT", price, shares))
            cash = 0.0
        elif crossed_down and shares > 0.0:
            cash = shares * price
            result.trades.append(Trade(points[i].date, "VENTE", price, shares))
            shares = 0.0

    result.final_equity = cash + shares * prices[-1]
    result.buy_and_hold_final = starting_capital / prices[0] * prices[-1]
    return result


def sparkline(values: list[float], width: int = 60) -> str:
    if len(values) > width:
        step = len(values) / width
        values = [values[int(i * step)] for i in range(width)]
    if len(values) < 2:
        return "(pas assez de donnees)"
    lo, hi = min(values), max(values)
    span = hi - lo or 1.0
    return "".join(
        SPARK_CHARS[min(len(SPARK_CHARS) - 1, int((v - lo) / span * (len(SPARK_CHARS) - 1)))]
        for v in values
    )


def print_report(
    points: list[PricePoint],
    result: BacktestResult,
    starting_capital: float,
    short_window: int,
    long_window: int,
) -> None:
    print("=== Bot de trading pedagogique - Croisement de moyennes mobiles ===")
    print(f"Periode analysee   : {points[0].date} -> {points[-1].date} ({len(points)} points)")
    print(f"Strategie          : SMA{short_window} / SMA{long_window}")
    print(f"Capital de depart  : {starting_capital:,.2f} EUR")
    print()

    print("Historique des prix (apercu):")
    print(f"  {sparkline([p.close for p in points])}")
    print()

    if not result.trades:
        print("Aucun signal d'achat/vente declenche sur cette periode.")
    else:
        print(f"Trades executes ({len(result.trades)}):")
        for trade in result.trades:
            print(f"  {trade.date:<12} {trade.action:<6} @ {trade.price:>10.2f} EUR ({trade.shares:.4f} unites)")
    print()

    strategy_return = (result.final_equity - starting_capital) / starting_capital * 100
    bh_return = (result.buy_and_hold_final - starting_capital) / starting_capital * 100

    print("Resultats:")
    print(f"  Strategie SMA{short_window}/{long_window} : {result.final_equity:>12,.2f} EUR  ({strategy_return:+.2f} %)")
    print(f"  Buy & Hold (reference)  : {result.buy_and_hold_final:>12,.2f} EUR  ({bh_return:+.2f} %)")
    print(f"  Nombre de trades        : {len(result.trades)}")
    print(f"  Drawdown maximum        : -{result.max_drawdown_pct:.2f} %")
    print()

    if strategy_return > bh_return:
        print("-> Sur cette periode precise, la strategie a fait MIEUX que buy & hold.")
    else:
        print("-> Sur cette periode precise, buy & hold a fait MIEUX que la strategie.")
    print(
        "\nRappel important : ce resultat ne concerne qu'UNE seule periode/serie de\n"
        "donnees. Une vraie evaluation de strategie necessite de tester sur de\n"
        "nombreuses periodes et plusieurs actifs, car un backtest gagnant ne\n"
        "garantit jamais des gains futurs (risque de surapprentissage)."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bot de trading pedagogique (backtest, croisement de moyennes mobiles)."
    )
    parser.add_argument(
        "--source", choices=["synthetic", "csv", "yfinance"], default="synthetic",
        help="Source des donnees de prix (defaut: synthetic).",
    )
    parser.add_argument("--days", type=int, default=250, help="Nombre de jours simules (source=synthetic).")
    parser.add_argument("--seed", type=int, default=None, help="Graine aleatoire (source=synthetic).")
    parser.add_argument("--csv-path", type=str, default=None, help="Chemin du fichier CSV (source=csv).")
    parser.add_argument("--ticker", type=str, default="AAPL", help="Symbole boursier (source=yfinance).")
    parser.add_argument("--period", type=str, default="1y", help="Periode historique, ex: 6mo, 1y, 5y (source=yfinance).")
    parser.add_argument("--interval", type=str, default="1d", help="Intervalle, ex: 1d, 1wk (source=yfinance).")
    parser.add_argument("--short-window", type=int, default=20, help="Fenetre de la moyenne mobile courte (defaut: 20).")
    parser.add_argument("--long-window", type=int, default=50, help="Fenetre de la moyenne mobile longue (defaut: 50).")
    parser.add_argument("--capital", type=float, default=10000.0, help="Capital de depart en EUR (defaut: 10000).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.short_window <= 0 or args.long_window <= 0:
        raise SystemExit("Les fenetres de moyenne mobile doivent etre superieures a 0.")
    if args.short_window >= args.long_window:
        raise SystemExit("--short-window doit etre strictement inferieur a --long-window.")
    if args.capital <= 0:
        raise SystemExit("Le capital de depart doit etre positif.")

    if args.source == "synthetic":
        points = load_synthetic(args.days, args.seed)
    elif args.source == "csv":
        if not args.csv_path:
            raise SystemExit("--csv-path est requis avec --source csv.")
        points = load_csv(args.csv_path)
    else:
        points = load_yfinance(args.ticker, args.period, args.interval)

    if len(points) <= args.long_window:
        raise SystemExit(
            f"Pas assez de donnees ({len(points)} points) pour une moyenne mobile de {args.long_window}."
        )

    result = run_backtest(points, args.short_window, args.long_window, args.capital)
    print_report(points, result, args.capital, args.short_window, args.long_window)


if __name__ == "__main__":
    main()
