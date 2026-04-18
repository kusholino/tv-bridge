/**
 * TV-Bridge Keyboard Module
 * 
 * Handhabt virtuelle Tastatur-Overlay.
 */

class KeyboardController {
    constructor(wsClient) {
        this.wsClient = wsClient;
        this.overlay = document.getElementById('keyboard-overlay');
        this.textarea = document.getElementById('keyboard-textarea');
        this.sendButton = document.getElementById('keyboard-send');
        this.closeButton = document.getElementById('keyboard-close');
        this.specialKeys = document.querySelectorAll('.special-key');
        
        this._init();
    }
    
    _init() {
        // Send Button
        this.sendButton.addEventListener('click', () => {
            this._sendText();
        });
        
        // Close Button
        this.closeButton.addEventListener('click', () => {
            this.hide();
        });
        
        // Special Keys
        this.specialKeys.forEach(button => {
            button.addEventListener('click', () => {
                const key = button.getAttribute('data-key');
                this._sendKey(key);
            });
        });
        
        // Enter-Key im Textarea sendet Text
        this.textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this._sendText();
            }
        });
    }
    
    show() {
        this.overlay.classList.remove('hidden');
        this.textarea.value = '';
        this.textarea.focus();
    }
    
    hide() {
        this.overlay.classList.add('hidden');
        this.textarea.value = '';
    }
    
    _sendText() {
        const text = this.textarea.value;
        
        if (text.length === 0) {
            return;
        }
        
        console.log('Sending text:', text);
        this.wsClient.sendText(text);
        
        this.textarea.value = '';
    }
    
    _sendKey(key) {
        console.log('Sending key:', key);
        this.wsClient.sendKey(key, 'press');
        
        // Auto-release nach kurzer Delay
        setTimeout(() => {
            this.wsClient.sendKey(key, 'release');
        }, 50);
    }
}
