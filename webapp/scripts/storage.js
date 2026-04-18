/**
 * TV-Bridge Storage Module
 * 
 * LocalStorage-Wrapper für persistente Client-Daten.
 */

const Storage = {
    KEYS: {
        DEVICE_TOKEN: 'tvbridge_device_token',
        DEVICE_ID: 'tvbridge_device_id',
        DEVICE_NAME: 'tvbridge_device_name',
        SETTINGS: 'tvbridge_settings'
    },
    
    // Device Token
    getDeviceToken() {
        return localStorage.getItem(this.KEYS.DEVICE_TOKEN);
    },
    
    setDeviceToken(token) {
        localStorage.setItem(this.KEYS.DEVICE_TOKEN, token);
    },
    
    clearDeviceToken() {
        localStorage.removeItem(this.KEYS.DEVICE_TOKEN);
    },
    
    // Device ID
    getDeviceId() {
        return localStorage.getItem(this.KEYS.DEVICE_ID);
    },
    
    setDeviceId(id) {
        localStorage.setItem(this.KEYS.DEVICE_ID, id);
    },
    
    clearDeviceId() {
        localStorage.removeItem(this.KEYS.DEVICE_ID);
    },
    
    // Device Name
    getDeviceName() {
        return localStorage.getItem(this.KEYS.DEVICE_NAME);
    },
    
    setDeviceName(name) {
        localStorage.setItem(this.KEYS.DEVICE_NAME, name);
    },
    
    clearDeviceName() {
        localStorage.removeItem(this.KEYS.DEVICE_NAME);
    },
    
    // Settings
    getSettings() {
        const settingsJson = localStorage.getItem(this.KEYS.SETTINGS);
        if (settingsJson) {
            try {
                return JSON.parse(settingsJson);
            } catch (e) {
                console.error('Error parsing settings:', e);
            }
        }
        
        // Default settings
        return {
            pointer_sensitivity: 1.0,
            pointer_acceleration: false,
            scroll_sensitivity: 1.0,
            natural_scroll: false,
            tap_to_click: true
        };
    },
    
    setSettings(settings) {
        localStorage.setItem(this.KEYS.SETTINGS, JSON.stringify(settings));
    },
    
    // Clear all
    clearAll() {
        this.clearDeviceToken();
        this.clearDeviceId();
        this.clearDeviceName();
        localStorage.removeItem(this.KEYS.SETTINGS);
    },
    
    // Check if device is paired
    isPaired() {
        return !!this.getDeviceToken();
    }
};
