/**
 * TV-Bridge Main Application
 * 
 * App-Lifecycle und Screen-Management.
 */

class App {
    constructor() {
        this.screens = {
            connect: document.getElementById('screen-connect'),
            remote: document.getElementById('screen-remote'),
            settings: document.getElementById('screen-settings')
        };
        
        this.statusDot = document.getElementById('connection-status').querySelector('.status-dot');
        this.statusText = document.getElementById('connection-status').querySelector('.status-text');
        this.remoteStatusDot = document.getElementById('remote-status-dot');
        this.remoteStatusText = document.getElementById('remote-status-text');
        
        this.pairingController = new PairingController();
        this.settingsController = new SettingsController(wsClient);
        this.keyboardController = new KeyboardController(wsClient);
        this.touchpad = null;
        
        this._init();
    }
    
    _init() {
        // Screen-Navigation
        document.getElementById('settings-button').addEventListener('click', () => {
            this.showScreen('settings');
        });
        
        document.getElementById('back-from-settings').addEventListener('click', () => {
            this.showScreen('remote');
        });
        
        // Remote-Buttons
        document.getElementById('btn-left-click').addEventListener('click', () => {
            wsClient.sendClick('left', 'click');
        });
        
        document.getElementById('btn-right-click').addEventListener('click', () => {
            wsClient.sendClick('right', 'click');
        });
        
        document.getElementById('btn-keyboard').addEventListener('click', () => {
            this.keyboardController.show();
        });
        
        // WebSocket Events
        wsClient.on('connected', () => {
            console.log('App: WebSocket connected');
            this._updateStatus('connecting', 'Connecting...');
        });
        
        wsClient.on('disconnected', () => {
            console.log('App: WebSocket disconnected');
            this._updateStatus('disconnected', 'Disconnected');
            this.showScreen('connect');
            this.pairingController.showReconnectSection();
        });
        
        wsClient.on('hello', (data) => {
            console.log('App: Server hello');
        });
        
        wsClient.on('auth_required', () => {
            console.log('App: Auth required');
            this.pairingController.showPairingSection();
        });
        
        wsClient.on('authenticated', (data) => {
            console.log('App: Authenticated', data);
            this._updateStatus('connected', 'Connected');
            this.settingsController.updateDeviceInfo(data.device_id, data.session_id);
            
            // Settings vom Server laden
            wsClient.getProfile('default');
            
            // Zu Remote-Screen wechseln
            setTimeout(() => {
                this.showScreen('remote');
            }, 500);
        });
        
        wsClient.on('auth_failed', (data) => {
            console.error('App: Auth failed', data);
            this._updateStatus('disconnected', 'Auth Failed');
            
            // Token löschen bei invalid_token
            if (data.reason === 'invalid_token') {
                Storage.clearAll();
                this.pairingController.showPairingSection();
            } else if (data.reason === 'device_revoked') {
                alert('Your device has been revoked. Please pair again.');
                Storage.clearAll();
                this.pairingController.showPairingSection();
            }
        });
        
        wsClient.on('max_reconnect_attempts', () => {
            console.error('App: Max reconnect attempts reached');
            this.pairingController.showRetryButton();
        });
        
        wsClient.on('device_revoked', (data) => {
            alert(`Device revoked: ${data.reason}`);
            Storage.clearAll();
            window.location.reload();
        });
        
        wsClient.on('profile_data', (data) => {
            console.log('App: Profile data received', data);
            // Settings lokal speichern und UI aktualisieren
            Storage.setSettings(data.settings);
            this.settingsController._loadSettings();
        });
        
        // Touchpad initialisieren
        const touchpadElement = document.getElementById('touchpad');
        this.touchpad = new Touchpad(touchpadElement, wsClient);
        
        // App starten
        this._start();
    }
    
    _start() {
        console.log('App: Starting');
        
        // Prüfen ob bereits gepairt
        if (Storage.isPaired()) {
            console.log('App: Device already paired, showing reconnect');
            this.pairingController.showReconnectSection();
            
            // WebSocket verbinden
            wsClient.connect();
        } else {
            console.log('App: Device not paired, showing pairing');
            this.pairingController.showPairingSection();
        }
    }
    
    showScreen(screenName) {
        Object.keys(this.screens).forEach(name => {
            if (name === screenName) {
                this.screens[name].classList.add('active');
            } else {
                this.screens[name].classList.remove('active');
            }
        });
    }
    
    _updateStatus(state, text) {
        // Connect-Screen Status
        this.statusText.textContent = text;
        this.statusDot.className = 'status-dot ' + state;
        
        // Remote-Screen Status
        this.remoteStatusText.textContent = text;
        this.remoteStatusDot.className = 'status-dot ' + state;
    }
}

// App starten wenn DOM geladen
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
});
