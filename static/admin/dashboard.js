document.addEventListener('DOMContentLoaded', function() {
    // Ładowanie danych statystycznych
    loadStatistics();
    
    // Ładowanie listy użytkowników
    loadUsers();
    
    // Ładowanie historii zmian
    loadChangeHistory();
    
    // Ładowanie ustawień systemu
    loadSystemSettings();
    
    // Obsługa formularza dodawania użytkownika
    document.getElementById('saveNewUser').addEventListener('click', addNewUser);
    
    // Obsługa formularza zmiany hasła
    document.getElementById('saveNewPassword').addEventListener('click', changePassword);
    
    // Obsługa formularza ustawień systemu
    document.getElementById('systemSettingsForm').addEventListener('submit', saveSystemSettings);
    
    // Test połączenia z Jirą
    document.getElementById('testJiraConnection').addEventListener('click', testJiraConnection);
    
    loadDashboardStats();
    loadRecentActivities();
    loadRecentErrors();
    
    // Odświeżaj dane co minutę
    setInterval(loadDashboardStats, 60000);
});

async function loadStatistics() {
    try {
        const response = await fetch('/api/admin/statistics');
        const data = await response.json();
        
        document.getElementById('usersCount').textContent = data.users_count;
        document.getElementById('projectsCount').textContent = data.projects_count;
        document.getElementById('worklogsCount').textContent = data.worklogs_count;
        document.getElementById('alertsCount').textContent = data.alerts_count;
    } catch (error) {
        console.error('Error loading statistics:', error);
        showError('Błąd podczas ładowania statystyk');
    }
}

async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users');
        const users = await response.json();
        
        const tbody = document.querySelector('#usersTable tbody');
        tbody.innerHTML = '';
        
        users.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${user.id}</td>
                <td>${user.user_name}</td>
                <td>${user.email}</td>
                <td>${user.role}</td>
                <td><span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">
                    ${user.is_active ? 'Aktywny' : 'Nieaktywny'}
                </span></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="editUser(${user.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${user.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading users:', error);
        showError('Błąd podczas ładowania użytkowników');
    }
}

async function loadChangeHistory() {
    try {
        const response = await fetch('/api/admin/change-history');
        const history = await response.json();
        
        const tbody = document.querySelector('#changeHistoryTable tbody');
        tbody.innerHTML = '';
        
        history.forEach(change => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${new Date(change.date).toLocaleString()}</td>
                <td>${change.user_name}</td>
                <td>${change.change_type}</td>
                <td>${change.old_value || '-'}</td>
                <td>${change.new_value || '-'}</td>
                <td>${change.changed_by}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading change history:', error);
        showError('Błąd podczas ładowania historii zmian');
    }
}

async function loadSystemSettings() {
    try {
        const response = await fetch('/api/admin/settings');
        const settings = await response.json();
        
        document.getElementById('jiraUrl').value = settings.jira_url || '';
        document.getElementById('syncInterval').value = settings.sync_interval || '24';
        document.getElementById('logRetention').value = settings.log_retention || '30';
        document.getElementById('logLevel').value = settings.log_level || 'INFO';
    } catch (error) {
        console.error('Error loading settings:', error);
        showError('Błąd podczas ładowania ustawień');
    }
}

async function addNewUser() {
    try {
        const userData = {
            user_name: document.getElementById('newUserName').value,
            email: document.getElementById('newUserEmail').value,
            role: document.getElementById('newUserRole').value,
            password: document.getElementById('newUserPassword').value
        };
        
        const response = await fetch('/api/admin/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });
        
        if (!response.ok) {
            throw new Error('Błąd podczas dodawania użytkownika');
        }
        
        // Zamknij modal i odśwież listę użytkowników
        const modal = bootstrap.Modal.getInstance(document.getElementById('addUserModal'));
        modal.hide();
        loadUsers();
        showSuccess('Użytkownik został dodany');
    } catch (error) {
        console.error('Error adding user:', error);
        showError('Błąd podczas dodawania użytkownika');
    }
}

function showSuccess(message) {
    // Implementacja wyświetlania komunikatu sukcesu
    alert(message); // Tymczasowo używamy alert, docelowo należy użyć lepszego UI
}

function showError(message) {
    Swal.fire({
        icon: 'error',
        title: 'Błąd',
        text: message,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000
    });
}

// Funkcje edycji i usuwania użytkowników
async function editUser(userId) {
    // TODO: Implementacja edycji użytkownika
    alert('Funkcja w przygotowaniu');
}

async function deleteUser(userId) {
    if (!confirm('Czy na pewno chcesz usunąć tego użytkownika?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Błąd podczas usuwania użytkownika');
        }
        
        loadUsers();
        showSuccess('Użytkownik został usunięty');
    } catch (error) {
        console.error('Error deleting user:', error);
        showError('Błąd podczas usuwania użytkownika');
    }
}

async function testJiraConnection() {
    try {
        const response = await fetch('/api/admin/test-jira-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: document.getElementById('jiraUrl').value
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess('Połączenie z Jirą działa poprawnie');
        } else {
            showError(data.error || 'Błąd połączenia z Jirą');
        }
    } catch (error) {
        console.error('Error testing Jira connection:', error);
        showError('Błąd podczas testowania połączenia z Jirą');
    }
}

async function loadDashboardStats() {
    try {
        const response = await fetch('/api/admin/dashboard/stats');
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Błąd podczas ładowania statystyk');
        }
        
        // Aktualizuj statystyki
        document.getElementById('usersCount').textContent = data.users_count;
        document.getElementById('worklogsCount').textContent = data.worklogs_count;
        document.getElementById('errorsCount').textContent = data.errors_count;
        document.getElementById('dbSize').textContent = formatSize(data.db_size);
        
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        showError('Błąd podczas ładowania statystyk');
    }
}

function formatSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`;
}

async function loadRecentActivities() {
    try {
        const response = await fetch('/api/admin/dashboard/activities');
        const activities = await response.json();
        
        if (!response.ok) {
            throw new Error(activities.error || 'Błąd podczas ładowania aktywności');
        }
        
        const tbody = document.querySelector('#activitiesTable tbody');
        tbody.innerHTML = '';
        
        if (activities.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center">Brak aktywności</td>
                </tr>
            `;
            return;
        }
        
        activities.forEach(activity => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${formatDate(activity.timestamp)}</td>
                <td>${activity.user}</td>
                <td>
                    <span class="text-muted">${activity.action}</span>
                    <small class="d-block text-muted">przez ${activity.performed_by}</small>
                </td>
            `;
            tbody.appendChild(tr);
        });
        
    } catch (error) {
        console.error('Error loading activities:', error);
        showError('Błąd podczas ładowania aktywności');
    }
}

async function loadRecentErrors() {
    try {
        const response = await fetch('/api/admin/dashboard/errors');
        const errors = await response.json();
        
        if (!response.ok) {
            throw new Error(errors.error || 'Błąd podczas ładowania błędów');
        }
        
        const tbody = document.querySelector('#errorsTable tbody');
        tbody.innerHTML = '';
        
        if (errors.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center">Brak błędów</td>
                </tr>
            `;
            return;
        }
        
        errors.forEach(error => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${formatDate(error.timestamp)}</td>
                <td>${error.module}</td>
                <td>
                    <span class="text-danger">${error.message}</span>
                </td>
            `;
            tbody.appendChild(tr);
        });
        
    } catch (error) {
        console.error('Error loading errors:', error);
        showError('Błąd podczas ładowania błędów');
    }
}

// Dodajmy też odświeżanie tabel co 30 sekund
setInterval(() => {
    loadRecentActivities();
    loadRecentErrors();
}, 30000);

function formatDate(timestamp) {
    return new Date(timestamp).toLocaleString('pl-PL', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function showLoading(element) {
    element.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Ładowanie...</span>
            </div>
        </div>
    `;
}

async function initCharts() {
    // Wykres worklogów
    const worklogsCtx = document.getElementById('worklogsChart').getContext('2d');
    const worklogsChart = new Chart(worklogsCtx, {
        type: 'line',
        data: {
            labels: [], // Ostatnie 7 dni
            datasets: [{
                label: 'Liczba worklogów',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Worklogi w ostatnich 7 dniach'
                }
            }
        }
    });

    // Wykres błędów
    const errorsCtx = document.getElementById('errorsChart').getContext('2d');
    const errorsChart = new Chart(errorsCtx, {
        type: 'bar',
        data: {
            labels: [], // Kategorie błędów
            datasets: [{
                label: 'Liczba błędów',
                data: [],
                backgroundColor: 'rgb(255, 99, 132)'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Błędy według kategorii'
                }
            }
        }
    });

    // Aktualizuj dane wykresów
    await updateCharts(worklogsChart, errorsChart);
}

async function updateCharts(worklogsChart, errorsChart) {
    try {
        const [worklogsData, errorsData] = await Promise.all([
            fetch('/api/admin/dashboard/worklogs-stats').then(r => r.json()),
            fetch('/api/admin/dashboard/errors-stats').then(r => r.json())
        ]);

        // Aktualizuj wykres worklogów
        worklogsChart.data.labels = worklogsData.labels;
        worklogsChart.data.datasets[0].data = worklogsData.data;
        worklogsChart.update();

        // Aktualizuj wykres błędów
        errorsChart.data.labels = errorsData.labels;
        errorsChart.data.datasets[0].data = errorsData.data;
        errorsChart.update();

    } catch (error) {
        console.error('Error updating charts:', error);
        showError('Błąd podczas aktualizacji wykresów');
    }
} 