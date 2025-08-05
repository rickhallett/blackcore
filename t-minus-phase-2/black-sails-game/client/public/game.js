// Game state
let socket = null;
let gameState = {
    authenticated: false,
    player: null,
    character: null,
    currentLocation: null,
    commandHistory: [],
    historyIndex: -1
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const authModal = document.getElementById('auth-modal');
    const token = localStorage.getItem('accessToken');
    
    if (token) {
        connectToGame(token);
    } else {
        authModal.style.display = 'flex';
    }
    
    // Setup input handler
    const input = document.getElementById('terminal-input');
    input.addEventListener('keydown', handleInput);
});

// Authentication
async function login() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            localStorage.setItem('accessToken', data.tokens.access);
            localStorage.setItem('refreshToken', data.tokens.refresh);
            gameState.player = data.player;
            
            if (data.player.character) {
                gameState.character = data.player.character;
                connectToGame(data.tokens.access);
            } else {
                showCharacterCreation();
            }
        } else {
            showError(data.error);
        }
    } catch (error) {
        showError('Connection failed. The seas are rough today.');
    }
}

async function register() {
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            localStorage.setItem('accessToken', data.tokens.access);
            localStorage.setItem('refreshToken', data.tokens.refresh);
            gameState.player = data.player;
            showCharacterCreation();
        } else {
            showError(data.error || data.errors[0].msg);
        }
    } catch (error) {
        showError('Connection failed. The seas are rough today.');
    }
}

function showLogin() {
    document.getElementById('login-form').style.display = 'block';
    document.getElementById('register-form').style.display = 'none';
    document.getElementById('auth-title').textContent = 'Welcome to Nassau';
}

function showRegister() {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('register-form').style.display = 'block';
    document.getElementById('auth-title').textContent = 'Join the Brotherhood';
}

function showCharacterCreation() {
    document.getElementById('auth-modal').style.display = 'none';
    document.getElementById('character-modal').style.display = 'flex';
}

// Character Creation
function updateAttributes() {
    const combat = parseInt(document.getElementById('combat').value);
    const sailing = parseInt(document.getElementById('sailing').value);
    const negotiation = parseInt(document.getElementById('negotiation').value);
    const deception = parseInt(document.getElementById('deception').value);
    
    document.getElementById('combat-value').textContent = combat;
    document.getElementById('sailing-value').textContent = sailing;
    document.getElementById('negotiation-value').textContent = negotiation;
    document.getElementById('deception-value').textContent = deception;
    
    const total = combat + sailing + negotiation + deception;
    const remaining = 20 - total;
    document.getElementById('points-remaining').textContent = remaining;
    
    // Disable sliders if over limit
    const inputs = document.querySelectorAll('.attribute input[type="range"]');
    inputs.forEach(input => {
        input.disabled = remaining < 0;
    });
}

async function createCharacter() {
    const name = document.getElementById('character-name').value;
    const faction = document.getElementById('faction-select').value;
    const combat = parseInt(document.getElementById('combat').value);
    const sailing = parseInt(document.getElementById('sailing').value);
    const negotiation = parseInt(document.getElementById('negotiation').value);
    const deception = parseInt(document.getElementById('deception').value);
    
    const total = combat + sailing + negotiation + deception;
    if (total > 20) {
        alert('Total attributes cannot exceed 20 points!');
        return;
    }
    
    try {
        const response = await fetch('/api/game/character', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify({
                name,
                faction,
                attributes: { combat, sailing, negotiation, deception }
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            gameState.character = data.character;
            document.getElementById('character-modal').style.display = 'none';
            connectToGame(localStorage.getItem('accessToken'));
        } else {
            showError(data.error);
        }
    } catch (error) {
        showError('Failed to create character');
    }
}

// Game Connection
function connectToGame(token) {
    document.getElementById('auth-modal').style.display = 'none';
    document.getElementById('character-modal').style.display = 'none';
    
    // Initialize socket connection
    socket = io({
        auth: { token }
    });
    
    socket.on('connect', () => {
        addOutput('Connected to Nassau...', 'system-message');
        socket.emit('authenticate', { token });
    });
    
    socket.on('authenticated', (data) => {
        if (data.success) {
            gameState.authenticated = true;
            gameState.player = data.player;
            updateUI();
            joinWorld();
        } else {
            showError('Authentication failed');
        }
    });
    
    socket.on('commandResult', handleCommandResult);
    socket.on('worldUpdate', handleWorldUpdate);
    socket.on('chatMessage', handleChatMessage);
    socket.on('actionResult', handleActionResult);
    socket.on('error', (data) => {
        addOutput(data.message, 'error');
    });
    
    socket.on('disconnect', () => {
        addOutput('Connection lost...', 'error');
    });
}

async function joinWorld() {
    try {
        const response = await fetch('/api/game/world/join', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            addOutput('You arrive in Nassau, the pirate republic...', 'narrative');
            addOutput('Type "help" for available commands.', 'system-message');
            
            // Get initial world state
            fetchWorldState(data.worldId);
        } else {
            showError(data.error);
        }
    } catch (error) {
        showError('Failed to join world');
    }
}

// Command Handling
function handleInput(event) {
    const input = event.target;
    
    if (event.key === 'Enter') {
        const command = input.value.trim();
        if (command) {
            processCommand(command);
            gameState.commandHistory.push(command);
            gameState.historyIndex = gameState.commandHistory.length;
            input.value = '';
        }
    } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        if (gameState.historyIndex > 0) {
            gameState.historyIndex--;
            input.value = gameState.commandHistory[gameState.historyIndex];
        }
    } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        if (gameState.historyIndex < gameState.commandHistory.length - 1) {
            gameState.historyIndex++;
            input.value = gameState.commandHistory[gameState.historyIndex];
        } else {
            gameState.historyIndex = gameState.commandHistory.length;
            input.value = '';
        }
    }
}

function processCommand(command) {
    addOutput(`> ${command}`, 'command-echo');
    
    // Local commands
    if (command.toLowerCase() === 'help') {
        showHelp();
        return;
    }
    
    if (command.toLowerCase() === 'clear') {
        clearOutput();
        return;
    }
    
    // Send to server
    const parts = command.split(' ');
    const cmd = parts[0];
    const args = parts.slice(1);
    
    socket.emit('gameCommand', { command: cmd, args });
}

function showHelp() {
    const helpText = `
Available Commands:
  Movement:
    move <location>  - Move to a new location
    sail <location>  - Sail to a distant location
    look [target]    - Examine your surroundings or a specific target
    map             - Show the map

  Interaction:
    talk <person>   - Speak with someone
    trade <person>  - Trade with merchants
    attack <target> - Initiate combat

  Character:
    status          - View your character status
    inventory       - Check your inventory
    ship           - View ship status
    reputation     - Check your reputation

  Quests:
    quests         - List active quests
    accept <quest> - Accept a new quest

  System:
    help           - Show this help
    clear          - Clear the terminal
    `;
    
    addOutput(helpText, 'system-message');
}

// Response Handlers
function handleCommandResult(result) {
    if (result.message) {
        addOutput(result.message);
    }
    
    if (result.narrative) {
        addOutput(result.narrative, 'narrative');
    }
    
    if (result.status) {
        displayStatus(result.status);
    }
    
    if (result.location) {
        gameState.currentLocation = result.location;
        updateLocationDisplay();
    }
    
    updateUI();
}

function handleWorldUpdate(update) {
    if (update.type === 'player_movement') {
        addOutput(`${update.playerName || 'Someone'} moves to ${update.to}.`, 'system-message');
    }
}

function handleChatMessage(data) {
    const prefix = data.channel === 'world' ? '[World]' : '[Global]';
    addOutput(`${prefix} ${data.playerName}: ${data.message}`, 'chat-message');
}

function handleActionResult(result) {
    if (result.message) {
        addOutput(result.message);
    }
    updateUI();
}

// UI Updates
function addOutput(text, className = '') {
    const output = document.getElementById('terminal-output');
    const line = document.createElement('div');
    line.className = `output-line ${className}`;
    line.textContent = text;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
}

function clearOutput() {
    document.getElementById('terminal-output').innerHTML = '';
}

function updateUI() {
    if (gameState.character) {
        document.getElementById('player-name').textContent = gameState.character.name;
        document.getElementById('location').textContent = gameState.character.location || 'Unknown';
        document.getElementById('gold').textContent = `Gold: ${gameState.character.gold}`;
        document.getElementById('health').textContent = `Health: ${gameState.character.health}`;
    }
}

function updateLocationDisplay() {
    document.getElementById('location').textContent = gameState.currentLocation;
}

function displayStatus(status) {
    const statsDisplay = document.getElementById('stats-display');
    statsDisplay.innerHTML = `
        <div class="stat-item">
            <span>Combat:</span>
            <span>${status.attributes.combat}/10</span>
        </div>
        <div class="stat-item">
            <span>Sailing:</span>
            <span>${status.attributes.sailing}/10</span>
        </div>
        <div class="stat-item">
            <span>Negotiation:</span>
            <span>${status.attributes.negotiation}/10</span>
        </div>
        <div class="stat-item">
            <span>Deception:</span>
            <span>${status.attributes.deception}/10</span>
        </div>
        <div class="stat-item">
            <span>Crew Loyalty:</span>
            <div class="stat-bar">
                <div class="stat-fill" style="width: ${status.resources.crew_loyalty}%"></div>
            </div>
        </div>
    `;
}

async function fetchWorldState(worldId) {
    try {
        const response = await fetch(`/api/game/world/${worldId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            updateWorldDisplay(data.world);
        }
    } catch (error) {
        console.error('Failed to fetch world state:', error);
    }
}

function updateWorldDisplay(worldData) {
    // Update map, other players, etc.
}

function showError(message) {
    const output = document.getElementById('terminal-output');
    if (output) {
        addOutput(message, 'error');
    } else {
        alert(message);
    }
}