console.log('Users.js loaded');

async function startJiraImport() {
    try {
        console.log('Starting JIRA import...');
        
        Swal.fire({
            title: 'Import Users',
            text: 'Importing users from JIRA...',
            icon: 'info',
            allowOutsideClick: false,
            showConfirmButton: false,
            willOpen: () => {
                Swal.showLoading();
            }
        });

        const response = await fetch('/admin/sync/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            await Swal.fire({
                title: 'Success!',
                text: 'Users imported successfully',
                icon: 'success'
            });
            location.reload();
        } else {
            throw new Error(data.message || 'Error during import');
        }
    } catch (error) {
        console.error('Import error:', error);
        Swal.fire({
            title: 'Error!',
            text: error.message || 'Failed to import users',
            icon: 'error'
        });
    }
}

// Funkcja zapisująca role użytkownika
async function saveUserRoles() {
    const userId = document.getElementById('editUserId').value;
    if (!userId) {
        Swal.fire('Błąd', 'Nie można zidentyfikować użytkownika', 'error');
        return;
    }

    // Pobierz zaznaczone role
    const selectedRoles = Array.from(document.querySelectorAll('.role-checkbox:checked'))
        .map(cb => parseInt(cb.value));

    console.log('Saving roles for user:', userId, 'Selected roles:', selectedRoles);

    try {
        const response = await fetch('/admin/users/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({
                id: userId,
                roles: selectedRoles
            })
        });

        const data = await response.json();
        console.log('Server response:', data);
        
        if (response.ok) {
            // Zamknij modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('userEditModal'));
            modal.hide();
            
            // Pokaż sukces
            await Swal.fire({
                title: 'Sukces!',
                text: 'Role zostały zaktualizowane',
                icon: 'success'
            });

            // Odśwież stronę
            window.location.reload();
        } else {
            throw new Error(data.message || 'Wystąpił błąd podczas zapisywania ról');
        }
    } catch (error) {
        console.error('Error:', error);
        Swal.fire({
            title: 'Błąd!',
            text: error.message || 'Wystąpił błąd podczas zapisywania ról',
            icon: 'error'
        });
    }
}

// Pojedyncza funkcja inicjalizująca wszystko
document.addEventListener('DOMContentLoaded', function() {
    console.log('Users.js loaded');
    
    // Inicjalizacja DataTable
    const usersTable = $('#usersTable').DataTable({
        pageLength: 10,
        order: [[0, 'asc']]
    });
    
    // Initialize Select2 for roles
    $('.select2').select2({
        theme: 'bootstrap4'
    });

    // Handle form submission
    const addUserForm = document.getElementById('addUserForm');
    if (addUserForm) {
        addUserForm.addEventListener('submit', saveUser);
    }

    // Reset form when modal is opened for new user
    $('#addUserModal').on('show.bs.modal', function(event) {
        const button = event.relatedTarget;
        const userId = button ? button.dataset.userId : null;
        const form = this.querySelector('form');
        
        form.reset();
        if (userId) {
            form.dataset.userId = userId;
            $('.modal-title').text('Edit User');
            $('#password-field').hide();
            
            // Load user data
            fetch(`/admin/users/${userId}`)
                .then(response => response.json())
                .then(user => {
                    form.querySelector('[name=username]').value = user.username;
                    form.querySelector('[name=email]').value = user.email;
                    form.querySelector('[name=display_name]').value = user.display_name || '';
                    form.querySelector('[name=is_active]').checked = user.is_active;
                    $(form.querySelector('[name=roles]')).val(user.roles.map(r => r.id)).trigger('change');
                })
                .catch(console.error);
        } else {
            delete form.dataset.userId;
            $('.modal-title').text('Add User');
            $('#password-field').show();
        }
    });

    // Handle user deletion
    document.querySelectorAll('.delete-user-btn').forEach(button => {
        button.addEventListener('click', async function() {
            const userName = this.dataset.userName;
            try {
                const result = await Swal.fire({
                    title: 'Are you sure?',
                    text: "This action cannot be undone!",
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#d33',
                    cancelButtonColor: '#3085d6',
                    confirmButtonText: 'Yes, delete!',
                    cancelButtonText: 'Cancel'
                });

                if (result.isConfirmed) {
                    const response = await fetch(`/admin/users/${userName}`, {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken()
                        }
                    });

                    if (!response.ok) {
                        throw new Error('Failed to delete user');
                    }

                    await Swal.fire(
                        'Deleted!',
                        'User has been deleted.',
                        'success'
                    );

                    window.location.reload();
                }
            } catch (error) {
                console.error('Error:', error);
                await Swal.fire({
                    title: 'Error!',
                    text: error.message || 'Failed to delete user',
                    icon: 'error'
                });
            }
        });
    });

    // Initialize import button
    const importBtn = document.getElementById('startImportBtn');
    if (importBtn) {
        importBtn.addEventListener('click', startJiraImport);
    }
});

// Funkcja pomocnicza do pobierania CSRF tokena
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

async function saveUser(event) {
    event.preventDefault();
    
    const form = document.getElementById('addUserForm');
    const userId = form.dataset.userId;
    const isEdit = !!userId;
    
    try {
        const formData = new FormData(form);
        const data = {
            username: formData.get('username'),
            email: formData.get('email'),
            display_name: formData.get('display_name'),
            is_active: formData.get('is_active') === 'on',
            roles: Array.from(formData.getAll('roles')).map(Number)
        };

        // Only include password for new users
        if (!isEdit && formData.get('password')) {
            data.password = formData.get('password');
        }

        const url = isEdit ? `/admin/users/${userId}` : '/admin/users/create';
        const method = isEdit ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            await Swal.fire({
                title: 'Success!',
                text: isEdit ? 'User updated successfully' : 'User created successfully',
                icon: 'success'
            });
            window.location.reload();
        } else {
            throw new Error(result.message || 'Error processing user');
        }
    } catch (error) {
        console.error('Error:', error);
        await Swal.fire({
            title: 'Error!',
            text: error.message || 'Failed to process user',
            icon: 'error'
        });
    }
} 