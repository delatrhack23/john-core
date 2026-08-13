# Éphémère — générateur d'e-mail jetable

Petit outil local pour **créer une adresse e-mail temporaire**, copier l'adresse, et lire les messages reçus (lien de confirmation, code à usage unique, etc.).

Il s'appuie sur des API publiques d'e-mail jetable ([mail.tm](https://docs.mail.tm/), avec [1secmail](https://www.1secmail.com/api/) en secours). Il **n'inscrit pas** de comptes Gmail, Outlook, Yahoo ou autres messageries durables.

## Lancer l'interface web

```bash
python3 examples/disposable-email/tempmail.py serve
```

Puis ouvrir [http://127.0.0.1:8765/](http://127.0.0.1:8765/). Aucune dépendance pip : Python 3.9+ suffit.

## Ligne de commande

```bash
# Créer une adresse et l'afficher
python3 examples/disposable-email/tempmail.py new -v

# Préfixe et domaine choisis
python3 examples/disposable-email/tempmail.py new --local demo-projet --domain mail.tm

# Domaines proposés par les fournisseurs
python3 examples/disposable-email/tempmail.py domains

# Lire la boîte de la dernière session (~/.ephemere-session.json)
python3 examples/disposable-email/tempmail.py inbox

# Surveiller l'arrivée des messages
python3 examples/disposable-email/tempmail.py watch --new
```

La session courante (adresse, jeton, mot de passe mail.tm) est enregistrée dans `~/.ephemere-session.json`.

## Tests

```bash
python3 examples/disposable-email/tests/test_tempmail.py
```

Les tests mockent le réseau. Ils ne créent pas de vraie boîte.

## Limites et usage raisonnable

- Les messages transitent par le fournisseur d'e-mail temporaire : considère la boîte comme **publique**.
- Ne l'utilise pas pour un compte bancaire, un réseau social durable, ou des données personnelles sensibles.
- L'outil sert à éviter le spam sur une adresse personnelle, ou à tester un flux d'inscription. Pas à industrialiser des comptes.
