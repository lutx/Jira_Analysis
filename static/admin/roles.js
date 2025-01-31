// Globalne zmienne
let roles = [];
let users = [];
let assignments = [];

// Na początku pliku
console.log('Roles.js loaded');

// Inicjalizacja przy załadowaniu strony
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing roles management');
    loadRoles();
    loadUsers();
    loadAssignments();
});

// Funkcje ładujące dane
async function loadRoles() {
    console.log('Loading roles...');
    try {
        const response = await fetch('/api/admin/roles');
        console.log('Roles response:', response);
        roles = await response.json();
        console.log('Loaded roles:', roles);
        renderRolesTable();
        updateRoleSelect();
    } catch (error) {
        console.error('Error loading roles:', error);
        showError('Błąd podczas ładowania ról');
    }
}

async function loadUsers() {
    try {
        const response = await fetch('/api/settings/users');
        const data = await response.json();
        users = data.users.filter(user => user.active); // tylko aktywni użytkownicy
        updateUserSelect();
    } catch (error) {
        console.error('Error loading users:', error);
        showError('Błąd podczas ładowania użytkowników');
    }
}

async function loadAssignments() {
    try {
        const response = await fetch('/api/admin/user-roles');
        assignments = await response.json();
        renderAssignmentsTable();
    } catch (error) {
        console.error('Error loading assignments:', error);
        showError('Błąd podczas ładowania przypisań');
    }
}

// Funkcje renderujące tabele
function renderRolesTable() {
    const tbody = document.getElementById('rolesTableBody');
    tbody.innerHTML = roles.map(role => `
        <tr>
            <td>${escapeHtml(role.name)}</td>
            <td>${escapeHtml(role.description || '')}</td>
            <td>${role.is_system ? '<span class="badge bg-primary">Systemowa</span>' : '<span class="badge bg-secondary">Własna</span>'}</td>
            <td>${new Date(role.created_at).toLocaleString()}</td>
            <td>
                ${!role.is_system ? `
                    <button class="btn btn-sm btn-outline-primary" onclick="editRole(${role.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteRole(${role.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                ` : ''}
            </td>
        </tr>
    `).join('');
}

function renderAssignmentsTable() {
    const tbody = document.getElementById('assignmentsTableBody');
    tbody.innerHTML = assignments.map(assignment => `
        <tr>
            <td>${escapeHtml(assignment.display_name)}</td>
            <td>${escapeHtml(assignment.email || '')}</td>
            <td>${escapeHtml(assignment.role_name)}</td>
            <td>${escapeHtml(assignment.assigned_by)}</td>
            <td>${new Date(assignment.assigned_at).toLocaleString()}</td>
            <td>
                <button class="btn btn-sm btn-outline-danger" onclick="removeAssignment(${assignment.id})">
                    <i class="bi bi-x-circle"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// Funkcje obsługi formularzy
function showAddRoleModal() {
    document.getElementById('roleId').value = '';
    document.getElementById('roleName').value = '';
    document.getElementById('roleDescription').value = '';
    document.getElementById('roleModalTitle').textContent = 'Dodaj Rolę';
    new bootstrap.Modal(document.getElementById('roleModal')).show();
}

function editRole(roleId) {
    const role = roles.find(r => r.id === roleId);
    if (role) {
        document.getElementById('roleId').value = role.id;
        document.getElementById('roleName').value = role.name;
        document.getElementById('roleDescription').value = role.description || '';
        document.getElementById('roleModalTitle').textContent = 'Edytuj Rolę';
        new bootstrap.Modal(document.getElementById('roleModal')).show();
    }
}

async function saveRole() {
    const roleId = document.getElementById('roleId').value;
    const name = document.getElementById('roleName').value.trim();
    const description = document.getElementById('roleDescription').value.trim();

    if (!name) {
        showError('Nazwa roli jest wymagana');
        return;
    }

    try {
        const method = roleId ? 'PUT' : 'POST';
        const url = roleId ? `/api/admin/roles/${roleId}` : '/api/admin/roles';

        const response = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, description })
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        await loadRoles();
        bootstrap.Modal.getInstance(document.getElementById('roleModal')).hide();
        showSuccess(roleId ? 'Rola została zaktualizowana' : 'Rola została utworzona');
    } catch (error) {
        console.error('Error saving role:', error);
        showError('Błąd podczas zapisywania roli');
    }
}

async function deleteRole(roleId) {
    if (!await confirm('Czy na pewno chcesz usunąć tę rolę?')) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/roles/${roleId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        await loadRoles();
        showSuccess('Rola została usunięta');
    } catch (error) {
        console.error('Error deleting role:', error);
        showError('Błąd podczas usuwania roli');
    }
}

// Funkcje pomocnicze
function updateUserSelect() {
    const select = document.getElementById('userSelect');
    select.innerHTML = '<option value="">Wybierz użytkownika...</option>' +
        users.map(user => `
            <option value="${user.key}">${escapeHtml(user.display_name)} (${escapeHtml(user.email || '')})</option>
        `).join('');
}

function updateRoleSelect() {
    const select = document.getElementById('roleSelect');
    select.innerHTML = '<option value="">Wybierz rolę...</option>' +
        roles.map(role => `
            <option value="${role.id}">${escapeHtml(role.name)}</option>
        `).join('');
}

async function assignRole() {
    const userKey = document.getElementById('userSelect').value;
    const roleId = document.getElementById('roleSelect').value;

    if (!userKey || !roleId) {
        showError('Wybierz użytkownika i rolę');
        return;
    }

    try {
        const response = await fetch('/api/admin/user-roles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_key: userKey, role_id: roleId })
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        await loadAssignments();
        bootstrap.Modal.getInstance(document.getElementById('assignRoleModal')).hide();
        showSuccess('Rola została przypisana');
    } catch (error) {
        console.error('Error assigning role:', error);
        showError('Błąd podczas przypisywania roli');
    }
}

async function removeAssignment(assignmentId) {
    if (!await confirm('Czy na pewno chcesz usunąć to przypisanie?')) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/user-roles/${assignmentId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        await loadAssignments();
        showSuccess('Przypisanie zostało usunięte');
    } catch (error) {
        console.error('Error removing assignment:', error);
        showError('Błąd podczas usuwania przypisania');
    }
}

// Funkcje pomocnicze UI
function showSuccess(message) {
    Swal.fire({
        icon: 'success',
        title: 'Sukces',
        text: message
    });
}

function showError(message) {
    Swal.fire({
        icon: 'error',
        title: 'Błąd',
        text: message
    });
}

async function confirm(message) {
    const result = await Swal.fire({
        icon: 'warning',
        title: 'Potwierdzenie',
        text: message,
        showCancelButton: true,
        confirmButtonText: 'Tak',
        cancelButtonText: 'Nie'
    });
    return result.isConfirmed;
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showAssignRoleModal() {
    document.getElementById('userSelect').value = '';
    document.getElementById('roleSelect').value = '';
    new bootstrap.Modal(document.getElementById('assignRoleModal')).show();
}

// Na początku każdej funkcji asynchronicznej
console.log('Starting function:', arguments.callee.name);

// Po każdym fetch
console.log('API Response:', response);

// Przy błędach
console.error('Error details:', {
    name: error.name,
    message: error.message,
    stack: error.stack
}); 