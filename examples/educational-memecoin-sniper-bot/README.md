# Simulateur pédagogique de bot de sniping de meme coins

Un vrai **bot avec une vraie logique de détection de risque** (liquidité
verrouillée, répartition des holders, "bundlers"...), exactement comme
un bot professionnel de sniping — mais appliqué à un **marché 100%
simulé**. Aucune connexion à un vrai wallet, aucun vrai token, aucun
argent réel.

> Ce projet répond à une question précise : *"un bot intelligent
> peut-il vraiment prédire quel meme coin va exploser ?"* La réponse,
> démontrée statistiquement par ce simulateur, est non — mais un bon
> filtre de sécurité réduit quand même nettement le risque de tomber
> sur une arnaque grossière (rug pull).

## Pourquoi un marché simulé et pas un vrai bot connecté à Axiom/Solana ?

Un vrai bot de sniping, avec de l'argent réel, mise sur un marché où
environ **98% des tokens s'effondrent** (données on-chain réelles de
Pump.fun, mars 2026 : sur 1,4 million de wallets, environ 96% ont fini
avec une perte ou moins de 500$ de gain, et seuls 2 wallets ont dépassé
1 million de dollars ce mois-là). Ce simulateur permet de coder et
tester la **même logique de détection**, en toute sécurité.

## Comment ça marche

Le script génère un flux de nouveaux tokens fictifs, chacun avec des
caractéristiques aléatoires réalistes :
- Liquidité verrouillée ou non (`lp_locked`)
- Pourcentage détenu par le développeur (`dev_holding_pct`)
- Concentration des 10 plus gros détenteurs (`top10_holder_pct`)
- Pourcentage détenu par des "bundlers" (`bundler_pct`)

Deux stratégies tradent sur exactement **le même flux de tokens**, pour
une comparaison directe et équitable :

1. **Bot intelligent** : n'achète que si le token respecte des critères
   de sécurité stricts (liquidité verrouillée, faible concentration des
   holders, etc.).
2. **Achat aveugle** : achète systématiquement 1 SOL sur *chaque*
   nouveau token, sans aucun filtre — le comportement d'un débutant qui
   clique sur tout ce qu'il voit.

## Utilisation

```bash
python3 sniper_bot_simulator.py
python3 sniper_bot_simulator.py --launches 2000 --trade-size 1 --seed 42
python3 sniper_bot_simulator.py --launches 500 --fee-rate 0.03
```

## Version "en direct" : ZACHXBTBOT

`live_sniper_bot.py` recree l'expérience complète d'un vrai bot de
sniping "en direct", mais entièrement simulée :

```bash
python3 live_sniper_bot.py
python3 live_sniper_bot.py --max-launches 30 --seed 42
python3 live_sniper_bot.py --fast          # enchaine les lancements plus vite
python3 live_sniper_bot.py --max-launches 0 # tourne en continu (Ctrl+C pour arreter)
```

Tape simplement Entrée pour lancer la surveillance. Le bot va ensuite :

1. Afficher une **alerte** à chaque "nouveau token" détecté, avec un
   lien **fictif** (`[SIMULATION] axiom.SIMULE/...`, jamais un vrai lien
   Axiom/Solana) et ses statistiques de risque.
2. **Décider automatiquement** d'investir 1 SOL (fictif) ou d'ignorer le
   token, selon le même filtre de sécurité que la version précédente.
3. **Suivre le prix en direct** (affiché tick par tick) puis vendre
   automatiquement.
4. Afficher un **portefeuille cumulé** qui évolue au fil des trades.

C'est exactement l'expérience d'un bot de sniping réel — surveillance,
alerte, décision automatique, achat/vente — mais sans jamais toucher à
un vrai wallet, un vrai token, ou un centime réel.

## Ce que les résultats montrent généralement

- Le **bot intelligent** a un taux de rug pull instantané bien plus bas
  que l'achat aveugle (le filtre fonctionne pour éviter les arnaques
  les plus grossières).
- Mais le **taux de "moonshot"** (gros gain) reste quasiment identique
  entre les deux stratégies — parce que la viralité d'un meme coin est
  fondamentalement imprévisible, même pour un bot très sophistiqué.
- Sur un grand nombre d'essais, le résultat net total des **deux**
  stratégies a de fortes chances d'être négatif, à cause du grand
  nombre de tokens qui échouent et des frais de swap cumulés.

## La vraie leçon de ce projet

Un bot "intelligent" apporte une vraie valeur : **il vous protège des
pièges les plus évidents**. Mais aucun bot, aussi sophistiqué soit-il,
ne peut prédire quel token va devenir viral — cette part reste
fondamentalement aléatoire. C'est la différence entre **réduire le
risque** (possible, utile) et **garantir un gain** (impossible, quelle
que soit la qualité du code).
