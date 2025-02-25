// Obsługa formularza logowania
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
});

async function handleLogin(e) {
    e.preventDefault();
    
    try {
        const formData = new FormData(e.target);
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify(Object.fromEntries(formData))
        });

        const data = await response.json();
        
        if (response.ok) {
            window.location.href = data.redirect || '/dashboard';
        } else {
            showError(data.message || 'Błąd logowania');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('Wystąpił błąd podczas logowania');
    }
}

function showError(message) {
    const errorDiv = document.getElementById('loginError');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('d-none');
    }
} 