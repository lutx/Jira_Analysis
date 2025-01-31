document.addEventListener('DOMContentLoaded', function() {
    loadUsers();
});

async function loadUsers() {
    try {
        const response = await fetch('/get_users');
        const users = await response.json();
        
        const tbody = document.querySelector('#usersTable tbody');
        tbody.innerHTML = '';
        
        users.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${user.user_name}</td>
                <td>${user.role}</td>
                <td>
                    <select class="form-select form-select-sm" onchange="updateUserRole('${user.user_name}', this.value)">
                        <option value="user" ${user.role === 'user' ? 'selected' : ''}>Użytkownik</option>
                        <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Administrator</option>
                        <option value="PM" ${user.role === 'PM' ? 'selected' : ''}>Project Manager</option>
                    </select>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading users:', error);
        showError('Błąd podczas ładowania użytkowników');
    }
}

async function updateUserRole(userName, newRole) {
    try {
        const response = await fetch('/update_user_role', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_name: userName,
                new_role: newRole
            })
        });
        
        if (!response.ok) {
            throw new Error('Błąd podczas aktualizacji roli');
        }
        
        showSuccess('Rola została zaktualizowana');
    } catch (error) {
        console.error('Error updating role:', error);
        showError('Błąd podczas aktualizacji roli');
    }
}

function showSuccess(message) {
    alert(message); // Tymczasowo używamy alert
}

function showError(message) {
    alert(message); // Tymczasowo używamy alert
} 