# Bot de trading pédagogique (backtest, croisement de moyennes mobiles)

Un vrai petit **bot de trading automatisé**, codé en Python, exécuté en
**backtest** (sur des données passées, réelles ou simulées) — pour
comprendre comment une stratégie de trading algorithmique est conçue et
évaluée, sans jamais risquer d'argent réel.

> Ce script n'envoie **aucun ordre réel** à un broker ou un exchange. Il
> ne fait que simuler, a posteriori, ce qu'aurait fait la stratégie sur
> des données historiques. Un résultat gagnant en backtest ne garantit
> **jamais** des gains futurs sur un vrai marché.

## Installation

Aucune dépendance n'est requise pour les sources `synthetic` et `csv`.
Pour utiliser de vraies données boursières (`--source yfinance`) :

```bash
pip install -r requirements.txt
```

## Utilisation

```bash
# Donnees simulees (aucune dependance, aucun acces reseau)
python3 moving_average_bot.py --source synthetic --days 250 --seed 42

# Vos propres donnees (fichier CSV avec colonnes "date,close")
python3 moving_average_bot.py --source csv --csv-path mes_prix.csv

# Vraies donnees boursieres historiques (necessite yfinance + internet)
python3 moving_average_bot.py --source yfinance --ticker AAPL --period 1y

# Personnaliser la strategie
python3 moving_average_bot.py --source yfinance --ticker MSFT --period 2y \
    --short-window 10 --long-window 30 --capital 5000
```

## La stratégie : croisement de moyennes mobiles (SMA crossover)

C'est l'une des stratégies de trading algorithmique les plus classiques
et les plus simples à comprendre :

- On calcule une **moyenne mobile courte** (ex: 20 derniers jours) et une
  **moyenne mobile longue** (ex: 50 derniers jours).
- Quand la moyenne courte **croise au-dessus** de la moyenne longue,
  c'est interprété comme le début d'une tendance haussière → **signal
  d'achat**.
- Quand la moyenne courte **croise en-dessous** de la moyenne longue,
  c'est interprété comme le début d'une tendance baissière → **signal
  de vente**.

Le bot investit 100% du capital disponible à chaque signal d'achat, et
revend tout à chaque signal de vente (pas de gestion de position
partielle, pour rester simple à comprendre).

## Ce que le rapport final vous montre

- La liste des trades exécutés (dates, prix, quantités).
- La performance de la stratégie vs une simple stratégie **buy & hold**
  (acheter au début, ne plus toucher) sur la même période — c'est la
  vraie question à se poser : *"est-ce que mon algorithme fait mieux que
  ne rien faire ?"*
- Le **drawdown maximum** : la plus grosse baisse subie par le
  portefeuille depuis un sommet, un indicateur clé du risque réel pris.

## Ce que cet exercice illustre (leçons importantes)

1. **La plupart des stratégies simples ne battent pas le marché** de
   façon fiable sur le long terme, en particulier après prise en compte
   des frais de transaction (non inclus ici, pour simplifier).
2. **Le backtesting a des limites** : une stratégie qui a bien marché
   sur une période passée précise peut très bien ne pas se reproduire
   (biais de surapprentissage / "curve fitting").
3. **Le choix des paramètres compte énormément** : essayez de faire
   varier `--short-window` et `--long-window`, vous verrez que les
   résultats changent radicalement — ce qui devrait vous rendre
   méfiant vis-à-vis de bots vendus avec des paramètres "magiques".
4. Un vrai bot de production devrait aussi gérer : les frais de
   transaction, le slippage (écart entre prix attendu et prix exécuté),
   la gestion du risque (stop-loss, taille de position), et être testé
   sur de nombreux actifs/périodes avant d'envisager du capital réel.

## Prochaine étape si vous voulez aller plus loin

Une fois cette logique bien comprise, l'étape suivante consisterait à
connecter ce type de stratégie à un **compte de démonstration (paper
trading)** chez un vrai broker ou exchange (qui fournit une API
compatible), pour observer son comportement en conditions réelles de
marché sans risquer d'argent — avant, éventuellement et avec beaucoup de
prudence, d'envisager un capital réel.
