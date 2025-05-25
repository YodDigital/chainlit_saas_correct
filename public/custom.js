// public/custom.js
if (typeof window.sendChainlitMessage === 'undefined') {
    window.sendChainlitMessage = function(message) {
        let success = false; // Track if the message was successfully sent

        // 1. Try WebSocket
        if (window.chainlit && window.chainlit.socket) {
            try {
                window.chainlit.socket.emit('custom_message', message);
                success = true;
            } catch (e) {
                console.error("Error sending via WebSocket:", e);
            }
        }

        // 2. Try Built-in Message System
        if (!success && window.chainlit && window.chainlit.sendMessage) {
            try {
                window.chainlit.sendMessage(message);
                success = true;
            } catch (e) {
                console.error("Error sending via sendMessage:", e);
            }
        }

        // 3. Try postMessage (for iFrames)
        if (!success && window.parent && window.parent.postMessage) {
            try {
                window.parent.postMessage(message, '*');
                success = true;
            } catch (e) {
                console.error("Error sending via postMessage:", e);
            }
        }

        // 4. Try DOM Event Dispatch (Least Reliable)
        if (!success) {
            const messageInput = document.querySelector('[data-testid="chat-input"]') ||
                               document.querySelector('input[type="text"]') ||
                               document.querySelector('textarea');

            if (messageInput) {
                try {
                    const event = new CustomEvent('chainlit-params', { detail: message });
                    messageInput.dispatchEvent(event);
                    success = true;
                } catch (e) {
                    console.error("Error dispatching DOM event:", e);
                }            }
        }

        // 5. Try Global Chainlit Object (Least Reliable)
        if (!success && window.Chainlit && typeof window.Chainlit.emit === 'function') {
            try {
                window.Chainlit.emit('message', message);
                success = true;
            } catch (e) {
                console.error("Error emitting via window.Chainlit.emit:", e);
            }
        }

        // Log for debugging, even if sending failed
        console.log("Sending message to Chainlit:", message, "Success:", success);    };
}

window.onload = function() {
    const url = window.location.href;
    const urlParams = new URL(url).searchParams;
    const params = {};

    for (const [key, value] of urlParams.entries()) {
        try {
            params[key] = decodeURIComponent(value);
        } catch (e) {
            console.error("Error decoding URL parameter:", key, value, e);
            params[key] = value; // Use the raw value if decoding fails
        }
    }

    const message = {        type: "url_params",
        params: params,
        timestamp: new Date().toISOString()
    };

    window.sendChainlitMessage(message);

    try {
        sessionStorage.setItem('chainlit_url_params', JSON.stringify(params));
    } catch (e) {
        console.error("Error storing params in sessionStorage:", e);
    }

    window.urlParams = params;
};

