/**
 * TV-Bridge REST API Client
 * 
 * Kommunikation via REST statt WebSockets.
 */

class RestClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.token = null;
        this.authenticated = false;
        this.eventHandlers = {};
    }
    
    on(event, handler) {
        this.eventHandlers[event] = handler;
    }
    
    _emit(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event](data);
        }
    }
    
    setToken(token) {
        this.token = token;
        this.authenticated = true;
        this._emit('authenticated', { device_token: token });
    }
    
    clearToken() {
        this.token = null;
        this.authenticated = false;
    }
    
    async _request(endpoint, method = 'GET', body = null) {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        const options = {
            method,
            headers
        };
        
        if (body) {
            options.body = JSON.stringify(body);
        }
        
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, options);
            
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    this._emit('auth_failed', { reason: 'invalid_token' });
                    this.clearToken();
                }
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`Request failed: ${endpoint}`, error);
            throw error;
        }
    }
    
    // Input methods
    async sendMove(dx, dy) {
        if (!this.authenticated) return;
        
        try {
            await this._request('/input/move', 'POST', { dx, dy });
        } catch (error) {
            console.error('Move failed:', error);
        }
    }
    
    async sendClick(button, action = 'click') {
        if (!this.authenticated) return;
        
        try {
            await this._request('/input/click', 'POST', { button, action });
        } catch (error) {
            console.error('Click failed:', error);
        }
    }
    
    async sendScroll(vertical, horizontal = 0) {
        if (!this.authenticated) return;
        
        try {
            await this._request('/input/scroll', 'POST', { vertical, horizontal });
        } catch (error) {
            console.error('Scroll failed:', error);
        }
    }
    
    async sendKey(key, action = 'press') {
        if (!this.authenticated) return;
        
        try {
            await this._request('/input/key', 'POST', { key, action });
        } catch (error) {
            console.error('Key failed:', error);
        }
    }
    
    async sendText(text) {
        if (!this.authenticated) return;
        
        try {
            await this._request('/input/text', 'POST', { text });
        } catch (error) {
            console.error('Text failed:', error);
        }
    }
    
    // Pairing
    async pair(pairingCode, deviceName) {
        try {
            const response = await this._request('/pair', 'POST', {
                pairing_code: pairingCode,
                device_name: deviceName
            });
            
            if (response.success) {
                this.setToken(response.device_token);
                return response;
            } else {
                throw new Error(response.message || 'Pairing failed');
            }
        } catch (error) {
            console.error('Pairing failed:', error);
            throw error;
        }
    }
    
    async checkPairingStatus() {
        try {
            const response = await this._request('/admin/pairing/status');
            return response.pairing_enabled;
        } catch (error) {
            console.error('Status check failed:', error);
            return false;
        }
    }
}

// Global instance
const restClient = new RestClient();
