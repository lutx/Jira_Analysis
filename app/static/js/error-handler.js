// Globalny handler błędów
window.onerror = function(msg, url, line, col, error) {
    // Ignoruj błędy CORS
    if (msg === 'Script error.' && !url) {
        return true;
    }

    try {
        const errorDetails = {
            message: msg,
            url: url,
            line: line,
            column: col,
            error: error ? error.stack : 'No error object'
        };

        console.error('Global error:', errorDetails);

        // Pokaż użytkownikowi informację o błędzie
        if (window.adminModals && window.adminModals.showError) {
            window.adminModals.showError('An error occurred. Please try again or contact support.');
        } else {
            alert('An error occurred. Please try again or contact support.');
        }

        // Wyślij błąd na serwer
        fetch('/api/log-error', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify(errorDetails)
        }).catch(console.error);

    } catch (e) {
        console.error('Error in error handler:', e);
    }

    return false; // Pozwól przeglądarce na domyślną obsługę błędu
};

// Handler dla nieobsłużonych odrzuceń Promise
window.onunhandledrejection = function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    
    if (window.adminModals && window.adminModals.showError) {
        window.adminModals.showError('An async operation failed. Please try again.');
    }
};

function logError(error) {
    // Add error logging with retry mechanism
    const retryCount = 3;
    const retryDelay = 1000; // 1 second

    function getCsrfToken() {
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        const inputToken = document.querySelector('input[name="csrf_token"]');
        return (metaToken && metaToken.content) || (inputToken && inputToken.value) || '';
    }

    function sendErrorLog(attempt = 1) {
        const errorData = {
            message: error.message || 'Unknown error',
            stack: error.stack || '',
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            attemptNumber: attempt
        };

        fetch('/api/log-error', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(errorData)
        })
        .catch(err => {
            console.error(`Error logging attempt ${attempt} failed:`, err);
            if (attempt < retryCount) {
                setTimeout(() => sendErrorLog(attempt + 1), retryDelay);
            }
        });
    }

    // Log to console first
    console.error('Caught error:', error);
    
    // Then try to send to server
    sendErrorLog();
}

window.addEventListener('error', function(event) {
    logError(event.error);
});

window.addEventListener('unhandledrejection', function(event) {
    logError(event.reason);
}); 