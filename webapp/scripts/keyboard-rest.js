/**
 * TV-Bridge Keyboard Module (REST Version)
 */

class KeyboardController {
    constructor(client) {
        this.client = client;
        this.overlay = document.getElementById('keyboard-overlay');
        this.textarea = document.getElementById('keyboard-textarea');
        this.sendButton = document.getElementById('keyboard-send');
        this.closeButton = document.getElementById('keyboard-close');
        this.specialKeys = document.querySelectorAll('.special-key');
        
        this._init();
    }
    
    _init() {
        this.sendButton.addEventListener('click', () => {
            this._sendText();
        });
        
        this.closeButton.addEventListener('click', () => {
            this.hide();
        });
        
        this.specialKeys.forEach(button => {
            button.addEventListener('click', () => {
                const key = button.getAttribute('data-key');
                this._sendKey(key);
            });
        });
        
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
        this.client.sendText(text);
        
        this.textarea.value = '';
    }
    
    _sendKey(key) {
        console.log('Sending key:', key);
        this.client.sendKey(key, 'press');
        
        setTimeout(() => {
            this.client.sendKey(key, 'release');
        }, 50);
    }
}
