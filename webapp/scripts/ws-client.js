/**
 * TV-Bridge WebSocket Client
 * 
 * Handhabt WebSocket-Verbindung, Reconnect und Nachrichtenaustausch.
 */

class WSClient {
    constructor() {
        this.ws = null;
        this.url = this._getWebSocketURL();
        this.connected = false;
        this.authenticated = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.messageHandlers = {};
        this.sessionId = null;
        this.deviceId = null;
        this.deviceName = null;
        this.pingInterval = null;
    }
    
    _getWebSocketURL() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws`;
    }
    
    connect() {
        console.log('Connecting to WebSocket:', this.url);
        
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.connected = true;
            this.reconnectAttempts = 0;
            this._onConnected();
        };
        
        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this._handleMessage(message);
            } catch (e) {
                console.error('Error parsing message:', e);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.connected = false;
            this.authenticated = false;
            this._onDisconnected();
            this._attemptReconnect();
        };
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
        this.connected = false;
        this.authenticated = false;
    }
    
    _attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnect attempts reached');
            this._trigger('max_reconnect_attempts');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
            if (!this.connected) {
                this.connect();
            }
        }, delay);
    }
    
    _onConnected() {
        this._trigger('connected');
    }
    
    _onDisconnected() {
        this._trigger('disconnected');
        
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }
    
    _handleMessage(message) {
        const { type, payload } = message;
        
        console.log('Received message:', type, payload);
        
        switch (type) {
            case 'hello':
                this._handleHello(payload);
                break;
            
            case 'auth_ok':
                this._handleAuthOk(payload);
                break;
            
            case 'auth_failed':
                this._handleAuthFailed(payload);
                break;
            
            case 'ping':
                this._handlePing();
                break;
            
            case 'error':
                this._handleError(payload);
                break;
            
            case 'profile_data':
                this._trigger('profile_data', payload);
                break;
            
            case 'device_revoked':
                this._handleDeviceRevoked(payload);
                break;
            
            default:
                console.warn('Unknown message type:', type);
        }
    }
    
    _handleHello(payload) {
        console.log('Server hello:', payload);
        this._trigger('hello', payload);
        
        // Auto-auth wenn Token vorhanden
        const token = Storage.getDeviceToken();
        if (token) {
            this.authenticate(token);
        } else {
            this._trigger('auth_required');
        }
    }
    
    _handleAuthOk(payload) {
        console.log('Authentication successful:', payload);
        this.authenticated = true;
        this.sessionId = payload.session_id;
        this.deviceId = payload.device_id;
        this.deviceName = payload.device_name;
        
        // Ping-Interval starten
        this.pingInterval = setInterval(() => {
            // Pong wird automatisch vom Browser gesendet bei WebSocket ping
        }, 30000);
        
        this._trigger('authenticated', payload);
    }
    
    _handleAuthFailed(payload) {
        console.error('Authentication failed:', payload);
        this.authenticated = false;
        this._trigger('auth_failed', payload);
    }
    
    _handlePing() {
        this.sendMessage('pong', {});
    }
    
    _handleError(payload) {
        console.error('Server error:', payload);
        this._trigger('error', payload);
    }
    
    _handleDeviceRevoked(payload) {
        console.warn('Device revoked:', payload);
        this._trigger('device_revoked', payload);
        
        // Token löschen
        Storage.clearAll();
        
        // Nach Delay disconnecten
        setTimeout(() => {
            this.disconnect();
        }, payload.disconnect_in_seconds * 1000);
    }
    
    authenticate(token) {
        this.sendMessage('auth', {
            device_token: token,
            debug: false
        });
    }
    
    sendMessage(type, payload) {
        if (!this.connected) {
            console.warn('Cannot send message: Not connected');
            return;
        }
        
        const message = {
            type: type,
            protocol_version: '1.0',
            timestamp: Date.now(),
            payload: payload
        };
        
        this.ws.send(JSON.stringify(message));
    }
    
    // Input Events
    sendMove(dx, dy) {
        this.sendMessage('input_move', { dx, dy });
    }
    
    sendClick(button, action) {
        this.sendMessage('input_click', { button, action });
    }
    
    sendScroll(vertical, horizontal = 0) {
        this.sendMessage('input_scroll', { vertical, horizontal });
    }
    
    sendKey(key, action) {
        this.sendMessage('input_key', { key, action });
    }
    
    sendText(text) {
        this.sendMessage('text_commit', { text });
    }
    
    // Profile
    getProfile(profileName = 'default') {
        this.sendMessage('profile_get', { profile_name: profileName });
    }
    
    setProfile(profileName, settings) {
        this.sendMessage('profile_set', {
            profile_name: profileName,
            settings: settings
        });
    }
    
    // Event Handlers
    on(event, handler) {
        if (!this.messageHandlers[event]) {
            this.messageHandlers[event] = [];
        }
        this.messageHandlers[event].push(handler);
    }
    
    off(event, handler) {
        if (this.messageHandlers[event]) {
            this.messageHandlers[event] = this.messageHandlers[event].filter(h => h !== handler);
        }
    }
    
    _trigger(event, data) {
        if (this.messageHandlers[event]) {
            this.messageHandlers[event].forEach(handler => handler(data));
        }
    }
}

// Global instance
const wsClient = new WSClient();
