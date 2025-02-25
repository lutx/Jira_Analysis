// Inicjalizacja po załadowaniu strony
document.addEventListener('DOMContentLoaded', function() {
    // Inicjalizacja modala
    const userModal = document.getElementById('userModal');
    const userModalInstance = userModal ? new bootstrap.Modal(userModal) : null;

    // Funkcje do zarządzania użytkownikami
    window.editUser = function(userId) {
        fetch(`/admin/api/users/${userId}/roles`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('userId').value = userId;
                    document.getElementById('userEmail').value = data.user.email;
                    document.getElementById('userActive').checked = data.user.is_active;
                    
                    // Zaznacz role użytkownika
                    const rolesSelect = document.getElementById('userRoles');
                    Array.from(rolesSelect.options).forEach(option => {
                        option.selected = data.user_roles.some(role => role.id === parseInt(option.value));
                    });
                    
                    if (userModalInstance) {
                        userModalInstance.show();
                    }
                } else {
                    throw new Error(data.message || 'Unknown error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Wystąpił błąd podczas ładowania danych użytkownika: ' + error.message);
            });
    };

    window.saveUser = function() {
        const userId = document.getElementById('userId').value;
        const email = document.getElementById('userEmail').value;
        const isActive = document.getElementById('userActive').checked;
        const selectedRoles = Array.from(document.getElementById('userRoles').selectedOptions)
            .map(option => parseInt(option.value));

        // Aktualizuj dane użytkownika
        fetch(`/admin/api/users/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({
                email: email,
                is_active: isActive
            })
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // Aktualizuj role
                return Promise.all(selectedRoles.map(roleId => 
                    fetch(`/admin/api/users/${userId}/roles`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                        },
                        body: JSON.stringify({ role_id: roleId })
                    })
                ));
            } else {
                throw new Error(data.message || 'Unknown error');
            }
        })
        .then(() => {
            if (userModalInstance) {
                userModalInstance.hide();
            }
            location.reload();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Wystąpił błąd podczas zapisywania zmian: ' + error.message);
        });
    };

    window.deleteUser = function(userId) {
        if (confirm('Czy na pewno chcesz usunąć tego użytkownika?')) {
            fetch(`/admin/api/users/${userId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                }
            })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    location.reload();
                } else {
                    throw new Error(data.message || 'Unknown error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Wystąpił błąd podczas usuwania użytkownika: ' + error.message);
            });
        }
    };

    // Inicjalizacja tooltipów
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Inicjalizacja wyszukiwarki
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keyup', function(e) {
            const searchText = e.target.value.toLowerCase();
            const rows = document.getElementById('usersTable').getElementsByTagName('tr');
            
            Array.from(rows).forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchText) ? '' : 'none';
            });
        });
    }
}); 