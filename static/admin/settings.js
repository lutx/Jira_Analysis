document.addEventListener('DOMContentLoaded', function() {
    loadAppSettings();
    
    document.getElementById('appSettingsForm').addEventListener('submit', saveAppSettings);
});

async function loadAppSettings() {
    try {
        const response = await fetch('/api/admin/settings');
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
        console.error('Error loading app settings:', error);
        showError('Błąd podczas ładowania ustawień');
    }
}

async function saveAppSettings(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const settings = {};
    
    formData.forEach((value, key) => {
        settings[key] = value;
    });
    
    try {
        const response = await fetch('/api/admin/settings', {
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

// Funkcja do synchronizacji użytkowników
async function syncJiraUsers() {
    try {
        const button = document.querySelector('[onclick="syncJiraUsers()"]');
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-arrow-repeat spinning"></i> Synchronizacja...';
        
        const response = await fetch('/api/jira/users/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            const details = data.details;
            Swal.fire({
                title: 'Sukces',
                html: `
                    <p>${data.message}</p>
                    <div class="mt-3">
                        <p>Zsynchronizowano ${details.total_users} użytkowników:</p>
                        <ul class="text-left">
                            <li>Nowi użytkownicy: ${details.new_users}</li>
                            <li>Zaktualizowani użytkownicy: ${details.updated_users}</li>
                        </ul>
                    </div>
                `,
                icon: 'success'
            });
            
            updateLastSyncTime();
        } else {
            throw new Error(data.error || 'Błąd podczas synchronizacji');
        }
    } catch (error) {
        console.error('Error:', error);
        Swal.fire('Błąd', error.message, 'error');
    } finally {
        const button = document.querySelector('[onclick="syncJiraUsers()"]');
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-arrow-repeat"></i> Synchronizuj użytkowników';
        }
    }
}

// Funkcja pokazująca powiadomienie o nowych użytkownikach
function showNewUsersNotification(users) {
    const usersList = users.map(user => 
        `<li>${user.display_name} (${user.email})</li>`
    ).join('');
    
    Swal.fire({
        title: 'Nowi użytkownicy',
        html: `
            <p>Dodano następujących użytkowników:</p>
            <ul class="text-left">
                ${usersList}
            </ul>
        `,
        icon: 'info'
    });
}

// Funkcja ładująca mapowania ról
async function loadRolesMappings() {
    try {
        const response = await fetch('/api/admin/role-mappings');
        const mappings = await response.json();
        
        const tbody = document.getElementById('rolesMappingTable');
        tbody.innerHTML = '';
        
        mappings.forEach(mapping => {
            tbody.innerHTML += `
                <tr>
                    <td>${mapping.jira_group}</td>
                    <td>${getRoleDisplayName(mapping.system_role)}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="editRoleMapping(${mapping.id})">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteRoleMapping(${mapping.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
    } catch (error) {
        console.error('Error:', error);
        Swal.fire('Błąd', 'Nie udało się załadować mapowań ról', 'error');
    }
}

// Funkcja pomocnicza do wyświetlania nazw ról
function getRoleDisplayName(role) {
    const roles = {
        'user': 'Użytkownik',
        'pm': 'Project Manager',
        'admin': 'Administrator',
        'superadmin': 'Super Administrator'
    };
    return roles[role] || role;
}

// Funkcja pokazująca modal dodawania mapowania
async function showAddMappingModal() {
    try {
        const response = await fetch('/api/jira/groups');
        const groups = await response.json();
        
        const select = document.getElementById('jiraGroup');
        select.innerHTML = groups.map(group => 
            `<option value="${group.name}">${group.name}</option>`
        ).join('');
        
        document.getElementById('roleMappingForm').reset();
        new bootstrap.Modal(document.getElementById('roleMappingModal')).show();
    } catch (error) {
        console.error('Error:', error);
        Swal.fire('Błąd', 'Nie udało się pobrać grup Jira', 'error');
    }
}

// Funkcja zapisująca mapowanie roli
async function saveRoleMapping() {
    try {
        const form = document.getElementById('roleMappingForm');
        const data = {
            jira_group: document.getElementById('jiraGroup').value,
            system_role: document.getElementById('systemRole').value
        };
        
        const response = await fetch('/api/admin/role-mappings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error('Błąd podczas zapisywania mapowania');
        }
        
        bootstrap.Modal.getInstance(document.getElementById('roleMappingModal')).hide();
        await loadRolesMappings();
        Swal.fire('Sukces', 'Mapowanie zostało zapisane', 'success');
    } catch (error) {
        console.error('Error:', error);
        Swal.fire('Błąd', error.message, 'error');
    }
}

// Funkcja do filtrowania użytkowników
async function filterUsers(params = {}) {
    try {
        const queryParams = new URLSearchParams({
            search: params.search || '',
            active_only: params.active_only || true,
            sort: params.sort || 'display_name',
            dir: params.dir || 'asc',
            page: params.page || 1,
            per_page: params.per_page || 50
        });

        const response = await fetch(`/api/jira/users?${queryParams}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Błąd podczas pobierania użytkowników');
        }
        
        return data;
    } catch (error) {
        console.error('Error:', error);
        Swal.fire('Błąd', error.message, 'error');
    }
}

// Funkcja do pobierania czasu ostatniej synchronizacji
async function updateLastSyncTime() {
    try {
        const response = await fetch('/api/jira/users?per_page=1');
        const data = await response.json();
        if (data.users && data.users[0]) {
            document.getElementById('lastSyncTime').textContent = 
                new Date(data.users[0].last_sync).toLocaleString();
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// Wywołaj przy załadowaniu strony
document.addEventListener('DOMContentLoaded', updateLastSyncTime);

async function testJiraConnection() {
    const button = document.querySelector('[onclick="testJiraConnection()"]');
    try {
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-plug spinning"></i> Testowanie...';
        
        const response = await fetch('/api/jira/test-connection');
        const data = await response.json();
        
        if (data.success) {
            Swal.fire({
                title: 'Połączenie działa',
                html: `
                    <p>Połączono jako:</p>
                    <p><strong>${data.user.name}</strong></p>
                    <p>${data.user.email}</p>
                `,
                icon: 'success'
            });
        } else {
            throw new Error(data.error || 'Błąd podczas testowania połączenia');
        }
    } catch (error) {
        console.error('Error:', error);
        Swal.fire('Błąd', error.message, 'error');
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-plug"></i> Testuj połączenie';
        }
    }
} 