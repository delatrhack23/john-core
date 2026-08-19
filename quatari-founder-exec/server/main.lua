local function notify(source, message)
    if not Config.Notifications then
        return
    end

    TriggerClientEvent('quatari-exec:client:notify', source, message)
end

local function playerHasPermission(source)
    if type(source) ~= 'number' or source <= 0 then
        return false
    end

    return IsPlayerAceAllowed(source, Config.AcePermission) == true
end

local function audit(source, target, code)
    if not Config.AuditLog then
        return
    end

    local name = GetPlayerName(source) or 'unknown'
    local preview = code:gsub('%s+', ' ')
    if #preview > 180 then
        preview = preview:sub(1, 180) .. '...'
    end

    print(('[quatari-exec] %s (id %s) exec %s: %s'):format(name, source, target, preview))
end

local function capturePrint(bucket)
    local original = print

    return function(...)
        local count = select('#', ...)
        local parts = {}

        for i = 1, count do
            parts[i] = tostring(select(i, ...))
        end

        bucket[#bucket + 1] = table.concat(parts, '\t')
        original(...)
    end, original
end

local function runLua(code)
    local prints = {}
    local hookedPrint, originalPrint = capturePrint(prints)
    local chunk, loadError, ok, result

    local ran, execError = pcall(function()
        print = hookedPrint
        chunk, loadError = load(code, '@quatari-exec', 't')
        if not chunk then
            return
        end
        ok, result = pcall(chunk)
    end)

    print = originalPrint

    if not ran then
        return false, tostring(execError)
    end

    if not chunk then
        return false, loadError
    end

    if not ok then
        return false, tostring(result)
    end

    local output = {}

    for i = 1, #prints do
        output[#output + 1] = prints[i]
    end

    if result ~= nil then
        output[#output + 1] = tostring(result)
    end

    if #output == 0 then
        return true, 'ok'
    end

    return true, table.concat(output, '\n')
end

RegisterNetEvent('quatari-exec:server:checkPermission', function()
    local source = source
    TriggerClientEvent('quatari-exec:client:setPermission', source, playerHasPermission(source))
end)

RegisterNetEvent('quatari-exec:server:run', function(payload)
    local source = source

    if type(payload) ~= 'table' then
        return
    end

    if not playerHasPermission(source) then
        TriggerClientEvent('quatari-exec:client:setPermission', source, false)
        notify(source, 'Acces refuse. Permission fondateur requise.')
        TriggerClientEvent('quatari-exec:client:result', source, false, 'permission deny')
        return
    end

    local target = payload.target
    local code = payload.code

    if target ~= 'server' and target ~= 'client' then
        TriggerClientEvent('quatari-exec:client:result', source, false, 'cible invalide')
        return
    end

    if type(code) ~= 'string' then
        TriggerClientEvent('quatari-exec:client:result', source, false, 'code invalide')
        return
    end

    code = code:gsub('^%s+', ''):gsub('%s+$', '')

    if code == '' then
        TriggerClientEvent('quatari-exec:client:result', source, false, 'code vide')
        return
    end

    if #code > Config.MaxCodeLength then
        TriggerClientEvent('quatari-exec:client:result', source, false, 'code trop long')
        return
    end

    audit(source, target, code)

    if target == 'client' then
        TriggerClientEvent('quatari-exec:client:run', source, code)
        return
    end

    local ok, output = runLua(code)
    TriggerClientEvent('quatari-exec:client:result', source, ok, output)
end)

AddEventHandler('playerJoining', function()
    local source = source

    SetTimeout(1500, function()
        if GetPlayerName(source) then
            TriggerClientEvent('quatari-exec:client:setPermission', source, playerHasPermission(source))
        end
    end)
end)
