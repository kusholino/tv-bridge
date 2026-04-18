/**
 * TV-Bridge Settings Module
 * 
 * Handhabt Einstellungen-UI.
 */

class SettingsController {
    constructor(wsClient) {
        this.wsClient = wsClient;
        this.sensitivitySlider = document.getElementById('sensitivity-slider');
        this.sensitivityValue = document.getElementById('sensitivity-value');
        this.scrollSensitivitySlider = document.getElementById('scroll-sensitivity-slider');
        this.scrollSensitivityValue = document.getElementById('scroll-sensitivity-value');
        this.pointerAccelerationCheckbox = document.getElementById('pointer-acceleration-checkbox');
        this.naturalScrollCheckbox = document.getElementById('natural-scroll-checkbox');
        this.tapToClickCheckbox = document.getElementById('tap-to-click-checkbox');
        this.saveButton = document.getElementById('save-settings-button');
        this.deviceIdDisplay = document.getElementById('device-id-display');
        this.sessionIdDisplay = document.getElementById('session-id-display');
        
        this._init();
    }
    
    _init() {
        // Slider-Werte anzeigen
        this.sensitivitySlider.addEventListener('input', () => {
            this.sensitivityValue.textContent = this.sensitivitySlider.value;
        });
        
        this.scrollSensitivitySlider.addEventListener('input', () => {
            this.scrollSensitivityValue.textContent = this.scrollSensitivitySlider.value;
        });
        
        // Save Button
        this.saveButton.addEventListener('click', () => {
            this._saveSettings();
        });
        
        // Lokale Settings laden
        this._loadSettings();
    }
    
    _loadSettings() {
        const settings = Storage.getSettings();
        
        this.sensitivitySlider.value = settings.pointer_sensitivity;
        this.sensitivityValue.textContent = settings.pointer_sensitivity;
        
        this.scrollSensitivitySlider.value = settings.scroll_sensitivity;
        this.scrollSensitivityValue.textContent = settings.scroll_sensitivity;
        
        this.pointerAccelerationCheckbox.checked = settings.pointer_acceleration;
        this.naturalScrollCheckbox.checked = settings.natural_scroll;
        this.tapToClickCheckbox.checked = settings.tap_to_click;
    }
    
    _saveSettings() {
        const settings = {
            pointer_sensitivity: parseFloat(this.sensitivitySlider.value),
            pointer_acceleration: this.pointerAccelerationCheckbox.checked,
            scroll_sensitivity: parseFloat(this.scrollSensitivitySlider.value),
            natural_scroll: this.naturalScrollCheckbox.checked,
            tap_to_click: this.tapToClickCheckbox.checked
        };
        
        // Lokal speichern
        Storage.setSettings(settings);
        
        // An Server senden
        if (this.wsClient.authenticated) {
            this.wsClient.setProfile('default', settings);
        }
        
        console.log('Settings saved:', settings);
        
        // Feedback
        this.saveButton.textContent = '✓ Saved';
        setTimeout(() => {
            this.saveButton.textContent = 'Save Settings';
        }, 2000);
    }
    
    updateDeviceInfo(deviceId, sessionId) {
        this.deviceIdDisplay.textContent = deviceId || '-';
        this.sessionIdDisplay.textContent = sessionId || '-';
    }
}
