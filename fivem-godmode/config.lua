Config = {}

-- Commande pour activer/desactiver le godmode
Config.Command = 'godmode'

-- Raccourci clavier optionnel (false pour desactiver)
-- Exemples: 'F7', 'F10', 'HOME'
Config.Keybind = 'F7'

-- Restreindre aux admins (ace permission)
Config.RequireAcePermission = true
Config.AcePermission = 'godmode.use'

-- Identifiants autorises si RequireAcePermission = false
-- Exemple: 'license:abc123', 'steam:11000010abcdef'
Config.AllowedIdentifiers = {}

-- Regeneration de vie / armure quand godmode actif
Config.RegenHealth = true
Config.RegenArmor = true
Config.MaxHealth = 200
Config.MaxArmor = 100

-- Proteger aussi le vehicule du joueur
Config.VehicleGodmode = true

-- Notifications dans le chat
Config.Notifications = true
