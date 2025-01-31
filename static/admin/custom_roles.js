console.log('Custom roles script loaded');

document.addEventListener('DOMContentLoaded', function() {
    loadCustomRoles();
});

async function loadCustomRoles() {
    try {
        console.log('Fetching custom roles...');
        const response = await fetch('/api/admin/custom-roles');
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const roles = await response.json();
        console.log('Fetched roles:', roles);
        
        const tbody = document.querySelector('#customRolesTable tbody');
        tbody.innerHTML = '';
        
        if (roles.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center">Brak zdefiniowanych ról</td>
                </tr>
            `;
            return;
        }
        
        roles.forEach(role => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${escapeHtml(role.name)}</td>
                <td>${escapeHtml(role.description || '')}</td>
                <td>${formatPermissions(role.permissions)}</td>
                <td>${escapeHtml(role.created_by)}</td>
                <td>${formatDate(role.created_at)}</td>
                <td>
                    <span class="badge ${role.is_active ? 'bg-success' : 'bg-danger'}">
                        ${role.is_active ? 'Aktywna' : 'Nieaktywna'}
                    </span>
                </td>
                <td>
                    ${getUserRole() === 'superadmin' ? `
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="editRole(${role.id})">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger me-1" onclick="deleteRole(${role.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-outline-info" onclick="viewRoleDetails(${role.id})">
                        <i class="bi bi-eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading roles:', error);
        showError('Błąd podczas ładowania ról');
    }
}

function formatPermissions(permissions) {
    return Object.entries(permissions)
        .filter(([_, value]) => value)
        .map(([key, _]) => `<span class="badge bg-info me-1">${formatPermissionName(key)}</span>`)
        .join('');
}

function formatPermissionName(key) {
    const names = {
        'view_reports': 'Raporty',
        'manage_users': 'Użytkownicy',
        'manage_projects': 'Projekty'
    };
    return names[key] || key;
}

function getUserRole() {
    const token = document.cookie.split('; ').find(row => row.startsWith('token='));
    if (token) {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.role;
    }
    return null;
}

async function saveRole() {
    try {
        const roleId = document.getElementById('roleId').value;
        const data = {
            name: document.getElementById('roleName').value,
            description: document.getElementById('roleDescription').value,
            permissions: {
                view_reports: document.getElementById('perm_view_reports').checked,
                manage_users: document.getElementById('perm_manage_users').checked,
                manage_projects: document.getElementById('perm_manage_projects').checked
            }
        };

        const url = roleId ? 
            `/api/admin/custom-roles/${roleId}` : 
            '/api/admin/custom-roles';
            
        const response = await fetch(url, {
            method: roleId ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Błąd podczas zapisywania roli');
        }

        bootstrap.Modal.getInstance(document.getElementById('roleModal')).hide();
        loadCustomRoles();
        showSuccess('Rola została zapisana');
    } catch (error) {
        console.error('Error saving role:', error);
        showError('Błąd podczas zapisywania roli');
    }
}

// Funkcje pomocnicze
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showSuccess(message) {
    Swal.fire({
        icon: 'success',
        title: message,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000
    });
}

function showError(message) {
    Swal.fire({
        icon: 'error',
        title: message,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000
    });
}

function showAddRoleModal() {
    document.getElementById('roleId').value = '';
    document.getElementById('roleName').value = '';
    document.getElementById('roleDescription').value = '';
    document.getElementById('perm_view_reports').checked = false;
    document.getElementById('perm_manage_users').checked = false;
    document.getElementById('perm_manage_projects').checked = false;
    
    document.getElementById('roleModalTitle').textContent = 'Dodaj Rolę';
    const modal = new bootstrap.Modal(document.getElementById('roleModal'));
    modal.show();
}

async function editRole(roleId) {
    try {
        const response = await fetch(`/api/admin/custom-roles/${roleId}`);
        const role = await response.json();
        
        document.getElementById('roleId').value = role.id;
        document.getElementById('roleName').value = role.name;
        document.getElementById('roleDescription').value = role.description || '';
        document.getElementById('perm_view_reports').checked = role.permissions.view_reports || false;
        document.getElementById('perm_manage_users').checked = role.permissions.manage_users || false;
        document.getElementById('perm_manage_projects').checked = role.permissions.manage_projects || false;
        
        document.getElementById('roleModalTitle').textContent = 'Edytuj Rolę';
        const modal = new bootstrap.Modal(document.getElementById('roleModal'));
        modal.show();
    } catch (error) {
        console.error('Error loading role:', error);
        showError('Błąd podczas ładowania roli');
    }
}

async function deleteRole(roleId) {
    try {
        const result = await Swal.fire({
            title: 'Czy na pewno?',
            text: "Nie będzie można cofnąć tej operacji!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Tak, usuń!',
            cancelButtonText: 'Anuluj'
        });
        
        if (result.isConfirmed) {
            const response = await fetch(`/api/admin/custom-roles/${roleId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error('Błąd podczas usuwania roli');
            }
            
            loadCustomRoles();
            showSuccess('Rola została usunięta');
        }
    } catch (error) {
        console.error('Error deleting role:', error);
        showError('Błąd podczas usuwania roli');
    }
}

async function viewRoleDetails(roleId) {
    try {
        const response = await fetch(`/api/admin/custom-roles/${roleId}`);
        const role = await response.json();
        
        Swal.fire({
            title: role.name,
            html: `
                <div class="text-start">
                    <p><strong>Opis:</strong> ${escapeHtml(role.description || '')}</p>
                    <p><strong>Uprawnienia:</strong></p>
                    <div>${formatPermissions(role.permissions)}</div>
                    <p><strong>Utworzono przez:</strong> ${escapeHtml(role.created_by)}</p>
                    <p><strong>Data utworzenia:</strong> ${formatDate(role.created_at)}</p>
                </div>
            `,
            width: '600px'
        });
    } catch (error) {
        console.error('Error loading role details:', error);
        showError('Błąd podczas ładowania szczegółów roli');
    }
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString('pl-PL', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
} 