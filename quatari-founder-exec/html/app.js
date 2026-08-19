const app = document.getElementById('app');
const serverName = document.getElementById('serverName');
const permBadge = document.getElementById('permBadge');
const closeBtn = document.getElementById('closeBtn');
const targetServer = document.getElementById('targetServer');
const targetClient = document.getElementById('targetClient');
const codeInput = document.getElementById('code');
const runBtn = document.getElementById('runBtn');
const statusEl = document.getElementById('status');
const outputEl = document.getElementById('output');

let currentTarget = 'server';
let allowed = false;
let resourceName = 'quatari-founder-exec';

if (typeof GetParentResourceName === 'function') {
    resourceName = GetParentResourceName();
}

function setPermission(isAllowed) {
    allowed = isAllowed === true;
    permBadge.textContent = allowed ? 'Fondateur' : 'Acces refuse';
    permBadge.classList.toggle('ok', allowed);
    permBadge.classList.toggle('deny', !allowed);
    runBtn.disabled = !allowed;
}

function setTarget(target) {
    currentTarget = target;
    targetServer.classList.toggle('active', target === 'server');
    targetClient.classList.toggle('active', target === 'client');
}

function setVisible(visible) {
    app.classList.toggle('hidden', !visible);
    if (visible) {
        codeInput.focus();
    }
}

function post(name, data) {
    return fetch(`https://${resourceName}/${name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json; charset=UTF-8' },
        body: JSON.stringify(data || {})
    });
}

function runCode() {
    if (!allowed) {
        statusEl.textContent = 'Permission fondateur manquante.';
        return;
    }

    const code = codeInput.value.trim();
    if (!code) {
        statusEl.textContent = 'Ecris du Lua avant d executer.';
        return;
    }

    statusEl.textContent = 'Execution...';
    outputEl.textContent = '';
    post('run', { target: currentTarget, code });
}

closeBtn.addEventListener('click', function () {
    post('close');
});

targetServer.addEventListener('click', function () {
    setTarget('server');
});

targetClient.addEventListener('click', function () {
    setTarget('client');
});

runBtn.addEventListener('click', runCode);

document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
        post('close');
        return;
    }

    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        runCode();
    }
});

window.addEventListener('message', function (event) {
    const data = event.data || {};

    if (data.action === 'setVisible') {
        if (data.serverName) {
            serverName.textContent = data.serverName;
        }
        if (typeof data.allowed === 'boolean') {
            setPermission(data.allowed);
        }
        setVisible(data.visible === true);
        return;
    }

    if (data.action === 'setPermission') {
        setPermission(data.allowed);
        return;
    }

    if (data.action === 'result') {
        const ok = data.ok === true;
        statusEl.textContent = ok ? 'Termine.' : 'Erreur.';
        outputEl.textContent = data.output || '';
        outputEl.style.color = ok ? '#7dba7a' : '#c45c4a';
    }
});
