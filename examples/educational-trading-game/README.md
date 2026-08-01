# Jeu pédagogique de trading (marché 100% fictif)

Un jeu en ligne de commande, avec une **interface stylée** (couleurs,
panneaux, tableaux, barre de progression) grâce à la bibliothèque
[`rich`](https://github.com/Textualize/rich), pour **apprendre les bases
du trading** (achat/vente, gestion du risque, stop-loss, diversification)
**sans risquer un seul euro réel**.

> Aucune connexion à un vrai broker, aucune donnée de marché réelle : les
> 5 actions et leurs prix sont entièrement fictifs et générés
> aléatoirement. Ceci est un outil d'apprentissage, pas un conseil en
> investissement, et ne garantit rien sur les marchés réels.

## Installation

```bash
pip install -r requirements.txt
```

## Lancer le jeu

```bash
python3 trading_game.py
```

Options disponibles :

```bash
python3 trading_game.py --days 30 --capital 10000   # personnaliser la durée et le capital
python3 trading_game.py --seed 42                    # rejouer exactement la meme partie
```

## Comment jouer

Chaque jour, les prix des 5 actions fictives évoluent (tendance +
volatilité aléatoire), et des actualités aléatoires peuvent faire
grimper ou chuter un secteur ou une action précise.

Commandes disponibles à chaque tour :

| Commande | Effet |
|---|---|
| `acheter TICKER QTE` | Acheter des actions (alias `buy`) |
| `vendre TICKER QTE` | Vendre des actions (alias `sell`) |
| `stop TICKER PRIX` | Poser un ordre stop-loss (vente automatique si le prix tombe à ce niveau) |
| `annulerstop TICKER` | Annuler un stop-loss |
| `info TICKER` | Voir le secteur, la volatilité et l'historique récent d'une action |
| `portefeuille` | Voir son portefeuille (alias `portfolio`) |
| `aide` | Revoir la liste des commandes (alias `help`) |
| `suivant` | Passer au jour suivant (alias `next`) |
| `quitter` | Terminer la partie immédiatement (alias `quit`) |

À la fin de la partie, un bilan récapitule votre performance et des
leçons concrètes (avez-vous diversifié ? avez-vous utilisé un
stop-loss ? etc.).

## Interface

Le jeu affiche :
- un tableau de marché en couleur (vert ▲ pour une hausse, rouge ▼ pour
  une baisse),
- un panneau "Portefeuille" avec vos positions et votre performance,
- une barre de progression indiquant l'avancement dans la partie,
- des panneaux dédiés pour les actualités et les déclenchements de
  stop-loss,
- un bilan final coloré (vert si performance positive, rouge sinon).

## Ce que ce jeu illustre

- **La diversification** : miser tout son capital sur une seule action
  est risqué ; répartir sur plusieurs actions/secteurs réduit ce risque.
- **Le stop-loss** : un ordre qui vend automatiquement une position si
  son prix chute trop, pour limiter les pertes.
- **La volatilité** : certaines actions bougent beaucoup plus que
  d'autres (voir la commande `info`), ce qui influence le risque pris.
- **L'impact des actualités** : les marchés réagissent à des événements
  imprévisibles (résultats d'entreprise, réglementation, rumeurs...).
- **La réalité statistique** : gagner une partie ne prouve pas qu'une
  stratégie est bonne ; il faut la tester sur de nombreuses parties
  (comme sur de vrais marchés, il faut se méfier du biais du survivant).

## Aller plus loin

Une fois à l'aise avec ce jeu, les prochaines étapes logiques pour
apprendre le vrai trading incluent :

- ouvrir un **compte de démonstration** (paper trading) chez un vrai
  broker, pour s'entraîner sur de vraies données sans argent réel,
- apprendre à lire de vrais graphiques (chandeliers japonais, moyennes
  mobiles, RSI...),
- étudier la gestion du risque en profondeur (taille de position, ratio
  risque/récompense, effet de levier).
