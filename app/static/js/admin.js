$(document).ready(function() {
    initializeRoleManagement();
    initializeUserManagement();
});

function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

function initializeRoleManagement() {
    // Obsługa przycisków akcji
    initializeRoleActions();
}

function handleModal(modalId, action = 'hide') {
    const modalElement = document.getElementById(modalId);
    if (!modalElement) return;
    
    if (action === 'show') {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    } else {
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) modal.hide();
    }
}

function handleRoleSubmit(form) {
    const name = form.querySelector('#roleName').value;
    if (!name) {
        showAlert('error', 'Nazwa roli jest wymagana');
        return;
    }

    const permissions = [];
    $('.permission-checkbox:checked').each(function() {
        permissions.push($(this).val());
    });

    const data = {
        name: name,
        description: form.querySelector('#roleDescription').value,
        permissions: permissions
    };

    const roleId = $('#roleId').val();
    const url = roleId ? `/admin/roles/${roleId}` : '/admin/roles/create';
    const method = roleId ? 'PUT' : 'POST';

    $.ajax({
        url: url,
        method: method,
        data: JSON.stringify(data),
        contentType: 'application/json',
        headers: {
            'Accept': 'application/json'
        },
        success: function(response) {
            handleModal('roleModal');
            showAlert('success', response.message);
            if (roleId) {
                updateRoleInTable(response.role);
            } else {
                addRoleToTable(response.role);
            }
            resetRoleForm();
        },
        error: function(xhr) {
            const errorMsg = xhr.responseJSON?.error || 'Wystąpił błąd podczas tworzenia roli';
            showAlert('error', errorMsg);
        }
    });
}

function initializeRoleActions() {
    // Edycja roli
    $(document).on('click', '.edit-role-btn', function() {
        const roleId = $(this).data('role-id');
        loadRoleForEdit(roleId);
    });

    // Usuwanie roli
    $(document).on('click', '.delete-role-btn', function() {
        const roleId = $(this).data('role-id');
        confirmDeleteRole(roleId);
    });
}

// Funkcje pomocnicze
function handleAjaxError(xhr) {
    showAlert('danger', 'Wystąpił błąd: ' + 
        (xhr.responseJSON?.error || 'Nieznany błąd'));
}

function showAlert(type, message) {
    Swal.fire({
        icon: type === 'success' ? 'success' : 'error',
        title: message,
        timer: 2000,
        showConfirmButton: false
    });
}

function addRoleToTable(role) {
    const newRow = `
        <tr id="role-${role.id}">
            <td>${escapeHtml(role.name)}</td>
            <td>${escapeHtml(role.description || '')}</td>
            <td>${formatPermissions(role.permissions)}</td>
            <td>${formatDate(role.created_at)}</td>
            <td>
                <button class="btn btn-sm btn-primary edit-role-btn" data-role-id="${role.id}">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-danger delete-role-btn" data-role-id="${role.id}">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>`;
    $('#rolesTableBody').append(newRow);
}

function resetRoleForm() {
    $('#roleForm')[0].reset();
    $('.permission-checkbox').prop('checked', false);
}

function formatPermissions(permissions) {
    return permissions.map(p => escapeHtml(p)).join(', ') || 'Brak';
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('pl-PL');
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function reloadAssignmentsTable() {
    $.get('/admin/roles/assignments', function(data) {
        $('#assignmentsTableBody').html(data);
    });
}

function initializeUserManagement() {
    // Tutaj możemy przenieść kod związany z zarządzaniem użytkownikami
}

function loadRoleForEdit(roleId) {
    $.get(`/admin/roles/${roleId}`, function(role) {
        $('#roleId').val(role.id);
        $('#roleName').val(role.name);
        $('#roleDescription').val(role.description);
        
        $('.permission-checkbox').prop('checked', false);
        role.permissions.forEach(perm => {
            $(`#perm${perm}`).prop('checked', true);
        });
        
        $('#roleModalTitle').text('Edytuj rolę');
        handleModal('roleModal', 'show');
    });
}

function confirmDeleteRole(roleId) {
    Swal.fire({
        title: 'Czy na pewno chcesz usunąć tę rolę?',
        text: "Tej operacji nie można cofnąć!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Tak, usuń',
        cancelButtonText: 'Anuluj'
    }).then((result) => {
        if (result.isConfirmed) {
            deleteRole(roleId);
        }
    });
}

function deleteRole(roleId) {
    $.ajax({
        url: `/admin/roles/${roleId}`,
        method: 'DELETE',
        success: function() {
            showAlert('success', 'Rola została usunięta');
            $(`#role-${roleId}`).remove();
        },
        error: handleAjaxError
    });
} 