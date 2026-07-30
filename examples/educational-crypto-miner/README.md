# Simulateur pédagogique de minage (Proof of Work)

Ce petit projet a un **but purement éducatif** : comprendre comment
fonctionne le minage de cryptomonnaie basé sur la preuve de travail
(*Proof of Work*, utilisée par exemple par Bitcoin), sans se connecter à
un vrai réseau, à un pool de minage, ou produire une quelconque
cryptomonnaie réelle.

> Ce n'est **ni** un logiciel de minage réel, **ni** connecté à une
> blockchain existante. Il ne doit pas être utilisé pour du "cryptojacking"
> (minage caché sur des machines sans consentement), ce qui serait
> illégal et contraire à l'usage prévu de ce code.

## Le principe (en résumé)

1. Un bloc contient des données (des transactions, dans un vrai réseau),
   l'horodatage, le hash du bloc précédent, et un compteur appelé `nonce`.
2. On calcule le hash SHA-256 de tout ce contenu.
3. Si le hash ne commence pas par un nombre suffisant de zéros (la
   **difficulté**), on incrémente le `nonce` et on recommence.
4. Le premier "mineur" qui trouve un hash valide peut ajouter son bloc à
   la chaîne (et, sur un vrai réseau, reçoit une récompense).

Plus la difficulté augmente, plus il faut essayer de valeurs de `nonce`
avant de trouver un hash valide (recherche exponentielle), ce qui explique
pourquoi le minage réel nécessite énormément de puissance de calcul et
d'électricité.

## Utilisation

```bash
# Miner un bloc avec la difficulté par défaut (4 zéros)
python3 miner.py

# Augmenter la difficulté (le calcul devient plus long)
python3 miner.py --difficulty 5

# Miner plusieurs blocs à la suite (chaque bloc pointe vers le précédent)
python3 miner.py --blocks 3 --difficulty 4
```

Le script affiche, pour chaque bloc miné :

- le `nonce` trouvé,
- le hash résultant,
- le nombre d'essais (hashs calculés) nécessaires,
- le temps écoulé et la vitesse en hashs/seconde (hashrate).

## Pour aller plus loin

- Essayez d'augmenter progressivement `--difficulty` (4, 5, 6, 7...) et
  observez comment le temps de calcul explose : c'est exactement ce
  mécanisme qui rend la falsification d'une blockchain très coûteuse en
  pratique.
- Le **Proof of Work** n'est pas la seule méthode : des réseaux comme
  Ethereum utilisent désormais le **Proof of Stake**, beaucoup moins
  gourmand en énergie, où les validateurs "misent" des jetons plutôt que
  de calculer des hashs.
