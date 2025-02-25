// Problem 1: Missing CSRF token handling
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

// Problem 2: Incorrect response handling
async function handleRoleSubmit() {
    try {
        // 1. Pobierz dane z formularza
        const formData = {
            name: document.getElementById('roleName').value.trim(),
            description: document.getElementById('roleDescription').value.trim(),
            permissions: Array.from(document.querySelectorAll('.permission-checkbox:checked'))
                            .map(cb => cb.value)
        };

        console.log('Form data:', formData);

        // 2. Walidacja danych
        if (!formData.name) {
            throw new Error('Nazwa roli jest wymagana');
        }

        // 3. Przygotuj żądanie
        const requestData = {
            name: formData.name,
            description: formData.description,
            permissions: formData.permissions
        };

        console.log('Request data:', requestData);

        const response = await fetch('/api/roles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                'Accept': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        // 4. Sprawdź odpowiedź
        console.log('Response status:', response.status);
        console.log('Response headers:', Object.fromEntries(response.headers));

        const responseText = await response.text();
        console.log('Raw response:', responseText);

        let data;
        try {
            data = responseText ? JSON.parse(responseText) : null;
        } catch (e) {
            console.error('Error parsing response:', e);
            throw new Error('Nieprawidłowa odpowiedź serwera');
        }

        if (!data) {
            throw new Error('Pusta odpowiedź z serwera');
        }

        if (!response.ok || data.status === 'error') {
            throw new Error(data.message || 'Wystąpił błąd podczas tworzenia roli');
        }

        // 5. Obsłuż sukces
        await Swal.fire({
            title: 'Sukces!',
            text: data.message || 'Rola została utworzona',
            icon: 'success'
        });

        // 6. Odśwież stronę
        window.location.reload();

    } catch (error) {
        console.error('Error:', error);
        await Swal.fire({
            title: 'Błąd!',
            text: error.message || 'Nie udało się utworzyć roli',
            icon: 'error'
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const rolesTable = $('#rolesTable').DataTable({
        pageLength: 10,
        order: [[0, 'asc']]
    });
    
    // Initialize Select2 for permissions
    $('.select2').select2({
        theme: 'bootstrap4',
        width: '100%'
    });

    // Handle role form submission
    $('#saveRole').click(function() {
        const form = $('#roleForm');
        const formData = new FormData(form[0]);
        
        $.ajax({
            url: form.attr('action') || window.location.pathname,
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                $('#roleModal').modal('hide');
                toastr.success('Role saved successfully');
                setTimeout(() => window.location.reload(), 1000);
            },
            error: function(xhr) {
                const errors = xhr.responseJSON?.errors || {'error': 'An error occurred while saving the role'};
                Object.entries(errors).forEach(([field, messages]) => {
                    const input = form.find(`[name="${field}"]`);
                    input.addClass('is-invalid');
                    input.next('.invalid-feedback').text(messages.join(', '));
                });
                toastr.error('Please correct the errors in the form');
            }
        });
    });

    // Handle role deletion
    $('.delete-role').click(function() {
        const roleId = $(this).data('role-id');
        const roleName = $(this).data('role-name');
        
        if (confirm(`Are you sure you want to delete the role "${roleName}"?`)) {
            $.ajax({
                url: `/admin/roles/${roleId}`,
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
                },
                success: function() {
                    toastr.success('Role deleted successfully');
                    $(`#role-${roleId}`).fadeOut();
                },
                error: function() {
                    toastr.error('Error deleting role');
                }
            });
        }
    });

    // Handle role editing
    $('.edit-role').click(function() {
        const roleId = $(this).data('role-id');
        
        // Load role data
        $.get(`/admin/roles/${roleId}`, function(data) {
            const form = $('#roleForm');
            form.find('[name="name"]').val(data.name);
            form.find('[name="description"]').val(data.description);
            form.find('[name="permissions"]').val(data.permissions).trigger('change');
            $('.modal-title').text('Edit Role');
        });
    });

    // Reset form on modal close
    $('#roleModal').on('hidden.bs.modal', function() {
        const form = $('#roleForm');
        form.trigger('reset');
        form.find('.is-invalid').removeClass('is-invalid');
        form.find('.invalid-feedback').text('');
        $('.modal-title').text('Add Role');
    });
});

function editRole(roleId) {
    fetch(`/admin/roles/${roleId}`)
        .then(response => response.json())
        .then(role => {
            $('#roleForm')[0].reset();
            $('#roleModal').modal('show');
            $('#roleForm [name=name]').val(role.name);
            $('#roleForm [name=description]').val(role.description);
            $('#roleForm [name=permissions]').val(role.permissions).trigger('change');
            $('#roleForm').data('roleId', roleId);
            $('.modal-title').text('Edit Role');
        })
        .catch(error => {
            console.error('Error loading role:', error);
            showNotification('Error loading role data', 'error');
        });
}

function saveRole() {
    const form = $('#roleForm');
    const roleId = form.data('roleId');
    const data = {
        name: form.find('[name=name]').val(),
        description: form.find('[name=description]').val(),
        permissions: form.find('[name=permissions]').val()
    };
    
    const url = roleId ? `/admin/roles/${roleId}` : '/admin/roles';
    const method = roleId ? 'PUT' : 'POST';
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            $('#roleModal').modal('hide');
            showNotification(result.message, 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving role:', error);
        showNotification('Error saving role', 'error');
    });
}

function deleteRole(roleId) {
    if (confirm('Are you sure you want to delete this role?')) {
        fetch(`/admin/roles/${roleId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                showNotification(result.message, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(result.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting role:', error);
            showNotification('Error deleting role', 'error');
        });
    }
} 