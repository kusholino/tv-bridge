/**
 * TV-Bridge Pairing Module (REST Version)
 */

class PairingController {
    constructor(client) {
        this.client = client;
        this.pairingSection = document.getElementById('pairing-section');
        this.reconnectSection = document.getElementById('reconnect-section');
        this.pairedInfo = document.getElementById('paired-info');
        this.pairingCodeInput = document.getElementById('pairing-code-input');
        this.deviceNameInput = document.getElementById('device-name-input');
        this.pairButton = document.getElementById('pair-button');
        this.pairingError = document.getElementById('pairing-error');
        this.retryButton = document.getElementById('retry-button');
        this.forgetDeviceButton = document.getElementById('forget-device-button');
        this.deviceNameDisplay = document.getElementById('device-name-display');
        
        this._init();
    }
    
    _init() {
        this.pairButton.addEventListener('click', () => {
            this._pair();
        });
        
        this.pairingCodeInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this._pair();
            }
        });
        
        this.pairingCodeInput.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
        });
        
        this.forgetDeviceButton.addEventListener('click', () => {
            this._forgetDevice();
        });
        
        this.retryButton.addEventListener('click', () => {
            window.location.reload();
        });
    }
    
    showPairingSection() {
        this.pairingSection.classList.remove('hidden');
        this.reconnectSection.classList.add('hidden');
        this.pairedInfo.classList.add('hidden');
    }
    
    showReconnectSection() {
        this.pairingSection.classList.add('hidden');
        this.reconnectSection.classList.remove('hidden');
        this.pairedInfo.classList.add('hidden');
        this.retryButton.classList.add('hidden');
    }
    
    showPairedInfo() {
        const deviceName = Storage.getDeviceName();
        this.deviceNameDisplay.textContent = deviceName || 'Unknown';
        
        this.pairingSection.classList.add('hidden');
        this.reconnectSection.classList.add('hidden');
        this.pairedInfo.classList.remove('hidden');
    }
    
    showRetryButton() {
        this.retryButton.classList.remove('hidden');
    }
    
    async _pair() {
        const code = this.pairingCodeInput.value.trim();
        const deviceName = this.deviceNameInput.value.trim();
        
        if (code.length !== 6) {
            this._showError('Please enter a 6-digit pairing code');
            return;
        }
        
        if (deviceName.length === 0) {
            this._showError('Please enter a device name');
            return;
        }
        
        this.pairButton.disabled = true;
        this.pairButton.textContent = 'Pairing...';
        this._hideError();
        
        try {
            const response = await this.client.pair(code, deviceName);
            
            Storage.setDeviceToken(response.device_token);
            Storage.setDeviceId(response.device_id);
            Storage.setDeviceName(response.device_name);
            
            console.log('Pairing successful!');
            
            window.location.reload();
        } catch (error) {
            this._showError(error.message || 'Pairing failed');
            this.pairButton.disabled = false;
            this.pairButton.textContent = 'Pair Device';
        }
    }
    
    _forgetDevice() {
        if (confirm('Are you sure you want to forget this device? You will need to pair again.')) {
            Storage.clearAll();
            window.location.reload();
        }
    }
    
    _showError(message) {
        this.pairingError.textContent = message;
        this.pairingError.classList.remove('hidden');
    }
    
    _hideError() {
        this.pairingError.classList.add('hidden');
    }
    
    async checkPairingStatus() {
        try {
            return await this.client.checkPairingStatus();
        } catch (error) {
            console.error('Error checking pairing status:', error);
            return false;
        }
    }
}
