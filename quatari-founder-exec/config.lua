Config = {}

-- Nom affiche dans l'interface et les logs
Config.ServerName = 'Quatari'

-- Commande pour ouvrir / fermer la console
Config.OpenCommand = 'qexec'

-- Raccourci clavier (false pour desactiver)
Config.Keybind = 'F8'

-- Permission ACE obligatoire (a donner uniquement aux fondateurs)
Config.AcePermission = 'quatari.founder'

-- Taille max du code Lua envoye
Config.MaxCodeLength = 8000

-- Journaliser chaque execution dans la console serveur
Config.AuditLog = true

-- Afficher les notifications chat
Config.Notifications = true
