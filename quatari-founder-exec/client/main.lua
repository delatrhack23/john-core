local hasPermission = false
local uiOpen = false

local function notify(message)
    if not Config.Notifications then
        return
    end

    TriggerEvent('chat:addMessage', {
        color = { 196, 151, 74 },
        multiline = false,
        args = { Config.ServerName, message }
    })
end

local function setUi(open)
    uiOpen = open
    SetNuiFocus(open, open)
    SendNUIMessage({
        action = 'setVisible',
        visible = open,
        serverName = Config.ServerName,
        allowed = hasPermission
    })
end

local function runLua(code)
    local prints = {}
    local originalPrint = print
    local chunk, loadError, ok, result

    local ran, execError = pcall(function()
        print = function(...)
            local count = select('#', ...)
            local parts = {}

            for i = 1, count do
                parts[i] = tostring(select(i, ...))
            end

            prints[#prints + 1] = table.concat(parts, '\t')
            originalPrint(...)
        end

        chunk, loadError = load(code, '@quatari-exec-client', 't')
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

RegisterNetEvent('quatari-exec:client:setPermission', function(allowed)
    hasPermission = allowed == true
    SendNUIMessage({
        action = 'setPermission',
        allowed = hasPermission
    })
end)

RegisterNetEvent('quatari-exec:client:notify', function(message)
    notify(message)
end)

RegisterNetEvent('quatari-exec:client:run', function(code)
    if not hasPermission then
        TriggerServerEvent('quatari-exec:server:checkPermission')
        SendNUIMessage({
            action = 'result',
            ok = false,
            output = 'permission deny'
        })
        return
    end

    local ok, output = runLua(code)
    SendNUIMessage({
        action = 'result',
        ok = ok,
        output = output
    })
end)

RegisterNetEvent('quatari-exec:client:result', function(ok, output)
    SendNUIMessage({
        action = 'result',
        ok = ok == true,
        output = output or ''
    })
end)

RegisterCommand(Config.OpenCommand, function()
    TriggerServerEvent('quatari-exec:server:checkPermission')

    if uiOpen then
        setUi(false)
        return
    end

    setUi(true)
end, false)

if Config.Keybind and Config.Keybind ~= false then
    RegisterKeyMapping(Config.OpenCommand, 'Ouvrir la console fondateur Quatari', 'keyboard', Config.Keybind)
end

RegisterNUICallback('close', function(_, cb)
    setUi(false)
    cb({ ok = true })
end)

RegisterNUICallback('run', function(data, cb)
    if type(data) ~= 'table' then
        cb({ ok = false })
        return
    end

    TriggerServerEvent('quatari-exec:server:run', {
        target = data.target,
        code = data.code
    })
    cb({ ok = true })
end)

CreateThread(function()
    TriggerServerEvent('quatari-exec:server:checkPermission')
end)
