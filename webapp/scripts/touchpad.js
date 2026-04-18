/**
 * TV-Bridge Touchpad Module
 * 
 * Handhabt Touch-Events und konvertiert sie in Mausbewegungen.
 */

class Touchpad {
    constructor(element, wsClient) {
        this.element = element;
        this.wsClient = wsClient;
        this.lastTouchPos = null;
        this.touchStartTime = null;
        this.touchCount = 0;
        this.eventBuffer = [];
        this.sendInterval = 16; // ~60 Hz
        this.lastSendTime = 0;
        
        this._init();
    }
    
    _init() {
        this.element.addEventListener('touchstart', this._onTouchStart.bind(this), { passive: false });
        this.element.addEventListener('touchmove', this._onTouchMove.bind(this), { passive: false });
        this.element.addEventListener('touchend', this._onTouchEnd.bind(this), { passive: false });
        this.element.addEventListener('touchcancel', this._onTouchCancel.bind(this), { passive: false });
        
        // Desktop-Support (für Testing)
        this.element.addEventListener('mousedown', this._onMouseDown.bind(this));
        this.element.addEventListener('mousemove', this._onMouseMove.bind(this));
        this.element.addEventListener('mouseup', this._onMouseUp.bind(this));
        this.element.addEventListener('mouseleave', this._onMouseUp.bind(this));
    }
    
    _onTouchStart(e) {
        e.preventDefault();
        
        this.touchCount = e.touches.length;
        this.touchStartTime = Date.now();
        
        if (this.touchCount === 1) {
            const touch = e.touches[0];
            this.lastTouchPos = {
                x: touch.clientX,
                y: touch.clientY
            };
        }
    }
    
    _onTouchMove(e) {
        e.preventDefault();
        
        if (this.touchCount === 1 && this.lastTouchPos) {
            const touch = e.touches[0];
            const dx = touch.clientX - this.lastTouchPos.x;
            const dy = touch.clientY - this.lastTouchPos.y;
            
            // Event buffern
            this.eventBuffer.push({ dx, dy });
            
            // Throttled senden
            const now = Date.now();
            if (now - this.lastSendTime >= this.sendInterval) {
                this._flushEventBuffer();
                this.lastSendTime = now;
            }
            
            this.lastTouchPos = {
                x: touch.clientX,
                y: touch.clientY
            };
        } else if (this.touchCount === 2) {
            // Zwei-Finger-Scroll
            const touch1 = e.touches[0];
            const touch2 = e.touches[1];
            
            if (this.lastTouchPos && this.lastTouchPos.y2) {
                const avgY = (touch1.clientY + touch2.clientY) / 2;
                const lastAvgY = (this.lastTouchPos.y + this.lastTouchPos.y2) / 2;
                const dy = avgY - lastAvgY;
                
                // Scroll-Event
                const scrollAmount = -dy / 10; // Normalisieren
                this.wsClient.sendScroll(scrollAmount);
            }
            
            this.lastTouchPos = {
                x: touch1.clientX,
                y: touch1.clientY,
                y2: touch2.clientY
            };
        }
    }
    
    _onTouchEnd(e) {
        e.preventDefault();
        
        // Flush remaining events
        this._flushEventBuffer();
        
        // Tap-to-click Detection
        const touchDuration = Date.now() - this.touchStartTime;
        
        if (touchDuration < 200 && this.touchCount === 1) {
            // Single Tap = Left Click
            console.log('Tap detected: Left click');
            this.wsClient.sendClick('left', 'click');
        } else if (touchDuration < 200 && this.touchCount === 2) {
            // Two-Finger Tap = Right Click
            console.log('Two-finger tap detected: Right click');
            this.wsClient.sendClick('right', 'click');
        }
        
        this.lastTouchPos = null;
        this.touchCount = 0;
    }
    
    _onTouchCancel(e) {
        this._onTouchEnd(e);
    }
    
    _flushEventBuffer() {
        if (this.eventBuffer.length === 0) {
            return;
        }
        
        // Coalesce: Alle Deltas summieren
        let totalDx = 0;
        let totalDy = 0;
        
        this.eventBuffer.forEach(event => {
            totalDx += event.dx;
            totalDy += event.dy;
        });
        
        // Senden
        if (Math.abs(totalDx) > 0.1 || Math.abs(totalDy) > 0.1) {
            this.wsClient.sendMove(totalDx, totalDy);
        }
        
        this.eventBuffer = [];
    }
    
    // Desktop Mouse Support
    _onMouseDown(e) {
        if (e.button !== 0) return; // Nur linke Maustaste
        
        this.lastTouchPos = {
            x: e.clientX,
            y: e.clientY
        };
    }
    
    _onMouseMove(e) {
        if (!this.lastTouchPos) return;
        
        const dx = e.clientX - this.lastTouchPos.x;
        const dy = e.clientY - this.lastTouchPos.y;
        
        this.wsClient.sendMove(dx, dy);
        
        this.lastTouchPos = {
            x: e.clientX,
            y: e.clientY
        };
    }
    
    _onMouseUp(e) {
        this.lastTouchPos = null;
    }
}
