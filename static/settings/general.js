document.addEventListener('DOMContentLoaded', function() {
    loadGeneralSettings();
});

async function loadGeneralSettings() {
    try {
        const response = await fetch('/api/settings/general');
        const settings = await response.json();
        
        // Wypełnij formularz ustawień
        Object.keys(settings).forEach(key => {
            const element = document.getElementById(key);
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = settings[key];
                } else {
                    element.value = settings[key];
                }
            }
        });
    } catch (error) {
        console.error('Error loading general settings:', error);
        showError('Błąd podczas ładowania ustawień');
    }
}

async function saveGeneralSettings(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const settings = {};
    
    formData.forEach((value, key) => {
        settings[key] = value;
    });
    
    try {
        const response = await fetch('/api/settings/general', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Błąd podczas zapisywania ustawień');
        }
        
        showSuccess('Ustawienia zostały zapisane');
    } catch (error) {
        console.error('Error saving settings:', error);
        showError(error.message);
    }
}

function showSuccess(message) {
    alert(message); // Tymczasowo używamy alert
}

function showError(message) {
    alert(message); // Tymczasowo używamy alert
} 