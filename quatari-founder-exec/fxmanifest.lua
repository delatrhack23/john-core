fx_version 'cerulean'
game 'gta5'
lua54 'yes'

name 'quatari-founder-exec'
author 'Quatari'
description 'Console Lua fondateur Quatari — execution serveur/client avec ACE'
version '1.0.0'

shared_script 'config.lua'

client_script 'client/main.lua'
server_script 'server/main.lua'

ui_page 'html/index.html'

files {
    'html/index.html',
    'html/style.css',
    'html/app.js'
}
