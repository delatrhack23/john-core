local function getPlayerIdentifiers(source)
    local identifiers = {}
    local count = GetNumPlayerIdentifiers(source)

    for i = 0, count - 1 do
        identifiers[#identifiers + 1] = GetPlayerIdentifier(source, i)
    end

    return identifiers
end

local function isIdentifierAllowed(source)
    if #Config.AllowedIdentifiers == 0 then
        return true
    end

    local playerIdentifiers = getPlayerIdentifiers(source)

    for _, allowed in ipairs(Config.AllowedIdentifiers) do
        for _, identifier in ipairs(playerIdentifiers) do
            if identifier == allowed then
                return true
            end
        end
    end

    return false
end

local function playerHasPermission(source)
    if Config.RequireAcePermission then
        return IsPlayerAceAllowed(source, Config.AcePermission)
    end

    return isIdentifierAllowed(source)
end

RegisterNetEvent('godmode:server:checkPermission', function()
    local source = source
    local allowed = playerHasPermission(source)
    TriggerClientEvent('godmode:client:setPermission', source, allowed)
end)

RegisterNetEvent('godmode:server:requestToggle', function()
    local source = source

    if not playerHasPermission(source) then
        TriggerClientEvent('godmode:client:setPermission', source, false)
        return
    end

    TriggerClientEvent('godmode:client:setPermission', source, true)
    TriggerClientEvent('godmode:client:toggle', source)
end)

AddEventHandler('playerConnecting', function(_, _, deferrals)
    local source = source

    CreateThread(function()
        Wait(1000)
        TriggerClientEvent('godmode:client:setPermission', source, playerHasPermission(source))
    end)
end)
