document.addEventListener('DOMContentLoaded', function() {
    loadUserSettings();
});

async function loadUserSettings() {
    try {
        const response = await fetch('/api/settings/users');
        const settings = await response.json();
        
        // Wypełnij formularz ustawień
        document.getElementById('defaultRole').value = settings.default_role || 'user';
        document.getElementById('autoActivate').checked = settings.auto_activate || false;
        
        // Załaduj listę użytkowników
        const usersResponse = await fetch('/get_users');
        const users = await usersResponse.json();
        
        const tbody = document.querySelector('#usersSettingsTable tbody');
        tbody.innerHTML = '';
        
        users.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${user.user_name}</td>
                <td>${user.role}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="resetUserPassword(${user.id})">
                        Reset hasła
                    </button>
                    <button class="btn btn-sm btn-outline-warning" onclick="deactivateUser(${user.id})">
                        Dezaktywuj
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading user settings:', error);
        showError('Błąd podczas ładowania ustawień użytkowników');
    }
}

function showError(message) {
    alert(message); // Tymczasowo używamy alert
} 