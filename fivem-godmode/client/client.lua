local godmodeEnabled = false
local hasPermission = false

local function notify(message)
    if not Config.Notifications then
        return
    end

    TriggerEvent('chat:addMessage', {
        color = { 0, 200, 100 },
        multiline = false,
        args = { 'Godmode', message }
    })
end

local function applyPedProtection(ped)
    SetEntityInvincible(ped, godmodeEnabled)
    SetPlayerInvincible(PlayerId(), godmodeEnabled)
    SetPedCanRagdoll(ped, not godmodeEnabled)
    SetEntityProofs(
        ped,
        godmodeEnabled,
        godmodeEnabled,
        godmodeEnabled,
        godmodeEnabled,
        godmodeEnabled,
        godmodeEnabled,
        godmodeEnabled,
        godmodeEnabled
    )

    if Config.RegenHealth then
        local health = GetEntityHealth(ped)
        if health < Config.MaxHealth then
            SetEntityHealth(ped, Config.MaxHealth)
        end
    end

    if Config.RegenArmor then
        local armor = GetPedArmour(ped)
        if armor < Config.MaxArmor then
            SetPedArmour(ped, Config.MaxArmor)
        end
    end
end

local function applyVehicleProtection(ped)
    if not Config.VehicleGodmode then
        return
    end

    if not IsPedInAnyVehicle(ped, false) then
        return
    end

    local vehicle = GetVehiclePedIsIn(ped, false)
    if vehicle == 0 then
        return
    end

    SetEntityInvincible(vehicle, godmodeEnabled)
    SetVehicleCanBeVisiblyDamaged(vehicle, not godmodeEnabled)
    SetVehicleTyresCanBurst(vehicle, not godmodeEnabled)
    SetVehicleEngineCanDegrade(vehicle, not godmodeEnabled)
end

local function setGodmode(state)
    godmodeEnabled = state
    local ped = PlayerPedId()
    applyPedProtection(ped)
    applyVehicleProtection(ped)

    if godmodeEnabled then
        notify('Godmode active.')
    else
        notify('Godmode desactive.')
    end
end

local function toggleGodmode()
    if Config.RequireAcePermission and not hasPermission then
        notify('Acces refuse. Permission admin requise.')
        return
    end

    if not Config.RequireAcePermission and #Config.AllowedIdentifiers > 0 and not hasPermission then
        notify('Acces refuse. Identifiant non autorise.')
        return
    end

    setGodmode(not godmodeEnabled)
end

RegisterNetEvent('godmode:client:setPermission', function(allowed)
    hasPermission = allowed == true
end)

RegisterNetEvent('godmode:client:toggle', function()
    toggleGodmode()
end)

RegisterCommand(Config.Command, function()
    TriggerServerEvent('godmode:server:requestToggle')
end, false)

if Config.Keybind and Config.Keybind ~= false then
    RegisterKeyMapping(Config.Command, 'Activer/desactiver le godmode', 'keyboard', Config.Keybind)
end

CreateThread(function()
    TriggerServerEvent('godmode:server:checkPermission')

    while true do
        if godmodeEnabled then
            local ped = PlayerPedId()
            applyPedProtection(ped)
            applyVehicleProtection(ped)
            Wait(0)
        else
            Wait(500)
        end
    end
end)

AddEventHandler('gameEventTriggered', function(eventName, data)
    if not godmodeEnabled then
        return
    end

    if eventName ~= 'CEventNetworkEntityDamage' then
        return
    end

    local victim = data[1]
    local ped = PlayerPedId()

    if victim ~= ped then
        return
    end

    applyPedProtection(ped)
end)
