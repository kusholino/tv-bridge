/**
 * TV-Bridge Main Application (REST Version)
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
        
        this.pairingController = new PairingController(restClient);
        this.settingsController = new SettingsController(restClient);
        this.keyboardController = new KeyboardController(restClient);
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
            restClient.sendClick('left', 'click');
        });
        
        document.getElementById('btn-right-click').addEventListener('click', () => {
            restClient.sendClick('right', 'click');
        });
        
        document.getElementById('btn-keyboard').addEventListener('click', () => {
            this.keyboardController.show();
        });
        
        // REST Client Events
        restClient.on('authenticated', (data) => {
            console.log('App: Authenticated');
            this._updateStatus('connected', 'Connected');
            this.settingsController.updateDeviceInfo(Storage.getDeviceId(), 'N/A');
            
            setTimeout(() => {
                this.showScreen('remote');
            }, 500);
        });
        
        restClient.on('auth_failed', (data) => {
            console.error('App: Auth failed', data);
            this._updateStatus('disconnected', 'Auth Failed');
            
            if (data.reason === 'invalid_token') {
                Storage.clearAll();
                this.pairingController.showPairingSection();
            }
        });
        
        // Touchpad initialisieren
        const touchpadElement = document.getElementById('touchpad');
        this.touchpad = new Touchpad(touchpadElement, restClient);
        
        // App starten
        this._start();
    }
    
    _start() {
        console.log('App: Starting');
        
        if (Storage.isPaired()) {
            console.log('App: Device already paired');
            const token = Storage.getDeviceToken();
            restClient.setToken(token);
            this._updateStatus('connected', 'Connected');
            this.showScreen('remote');
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
        this.statusText.textContent = text;
        this.statusDot.className = 'status-dot ' + state;
        
        this.remoteStatusText.textContent = text;
        this.remoteStatusDot.className = 'status-dot ' + state;
    }
}

// App starten wenn DOM geladen
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
});
