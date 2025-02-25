console.log('Roles.js loading...');

let isModalTransitioning = false;

function showModal(modalId) {
    if (isModalTransitioning) return;
    isModalTransitioning = true;
    
    const modal = document.getElementById(modalId);
    if (!modal) {
        console.error(`Modal with id ${modalId} not found`);
        return;
    }
    
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
    
    modal.addEventListener('shown.bs.modal', () => {
        isModalTransitioning = false;
    });
    
    modal.addEventListener('hidden.bs.modal', () => {
        isModalTransitioning = false;
    });
}

async function handleApiRequest(url, options) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                // Add CSRF token if you're using it
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        // Show error modal
        showErrorModal('Wystąpił błąd podczas komunikacji z serwerem. Spróbuj ponownie później.');
        throw error;
    }
}

// Obsługa otwierania modalu dodawania roli
document.getElementById('openAddRoleModalBtn')?.addEventListener('click', () => {
    console.log('Opening add role modal');
    showModal('addRoleModal');
});

// Obsługa dodawania roli
document.getElementById('submitAddRoleBtn')?.addEventListener('click', async () => {
    try {
        const roleName = document.getElementById('roleNameInput').value;
        if (!roleName) {
            alert('Proszę podać nazwę roli');
            return;
        }

        await handleApiRequest('/admin/roles/add', {
            method: 'POST',
            body: JSON.stringify({ name: roleName })
        });
        
        // Zamknij modal i odśwież stronę
        const modal = bootstrap.Modal.getInstance(document.getElementById('addRoleModal'));
        modal.hide();
        location.reload();
    } catch (error) {
        console.error('Error adding role:', error);
    }
});

// Obsługa edycji roli
document.querySelectorAll('.edit-role')?.forEach(button => {
    button.addEventListener('click', () => {
        const roleId = button.dataset.id;
        console.log('Edit role clicked for ID:', roleId);
        // TODO: Implement edit functionality
    });
});

// Obsługa usuwania roli
document.querySelectorAll('.delete-role')?.forEach(button => {
    button.addEventListener('click', async () => {
        const roleId = button.dataset.id;
        if (confirm('Czy na pewno chcesz usunąć tę rolę?')) {
            try {
                await handleApiRequest(`/admin/roles/delete/${roleId}`, {
                    method: 'DELETE'
                });
                location.reload();
            } catch (error) {
                console.error('Error deleting role:', error);
            }
        }
    });
});

console.log('Roles.js loaded successfully'); 