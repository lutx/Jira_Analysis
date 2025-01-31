let currentPage = 1;
let currentFilters = {
    search: '',
    active_only: true,
    sort: 'display_name',
    dir: 'asc',
    per_page: 50
};

// Inicjalizacja przy załadowaniu strony
document.addEventListener('DOMContentLoaded', function() {
    // Podpięcie eventów do filtrów
    document.getElementById('searchInput').addEventListener('input', debounce(refreshUsers, 300));
    document.getElementById('activeOnly').addEventListener('change', refreshUsers);
    document.getElementById('sortBy').addEventListener('change', refreshUsers);
    
    // Pierwsze pobranie użytkowników
    refreshUsers();
});

// Funkcja odświeżająca listę użytkowników
async function refreshUsers() {
    try {
        // Aktualizacja filtrów
        currentFilters.search = document.getElementById('searchInput').value;
        currentFilters.active_only = document.getElementById('activeOnly').checked;
        currentFilters.sort = document.getElementById('sortBy').value;
        currentFilters.page = currentPage;

        const data = await filterUsers(currentFilters);
        
        if (!data) return;

        // Aktualizacja tabeli
        const tbody = document.getElementById('usersList');
        tbody.innerHTML = '';

        data.users.forEach(user => {
            tbody.innerHTML += `
                <tr>
                    <td>${escapeHtml(user.display_name)}</td>
                    <td>${escapeHtml(user.username)}</td>
                    <td>${escapeHtml(user.email || '-')}</td>
                    <td>
                        <span class="badge ${user.active ? 'bg-success' : 'bg-secondary'}">
                            ${user.active ? 'Aktywny' : 'Nieaktywny'}
                        </span>
                    </td>
                    <td>${new Date(user.last_sync).toLocaleString()}</td>
                </tr>
            `;
        });

        // Aktualizacja paginacji
        updatePagination(data.page, data.pages);

    } catch (error) {
        console.error('Error:', error);
        Swal.fire('Błąd', error.message, 'error');
    }
}

// Funkcja aktualizująca paginację
function updatePagination(currentPage, totalPages) {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    // Przycisk "Poprzednia"
    pagination.innerHTML += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1})">Poprzednia</a>
        </li>
    `;

    // Numery stron
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            pagination.innerHTML += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
                </li>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            pagination.innerHTML += `
                <li class="page-item disabled">
                    <span class="page-link">...</span>
                </li>
            `;
        }
    }

    // Przycisk "Następna"
    pagination.innerHTML += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1})">Następna</a>
        </li>
    `;
}

// Funkcja zmiany strony
function changePage(page) {
    currentPage = page;
    refreshUsers();
}

// Pomocnicza funkcja do debounce
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Pomocnicza funkcja do escapowania HTML
function escapeHtml(unsafe) {
    return unsafe
        ? unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;")
        : '';
}

let users = []; // Przechowuje wszystkich użytkowników

async function loadUsers() {
    try {
        showLoading(document.querySelector('#usersTable tbody'));
        const response = await fetch('/api/admin/users');
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Błąd podczas ładowania użytkowników');
        }
        
        users = data; // Zapisz wszystkich użytkowników
        displayUsers(users); // Wyświetl użytkowników
        
    } catch (error) {
        console.error('Error loading users:', error);
        showError('Błąd podczas ładowania użytkowników');
    }
}

function displayUsers(usersToDisplay) {
    const tbody = document.querySelector('#usersTable tbody');
    tbody.innerHTML = '';
    
    usersToDisplay.forEach(user => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${user.user_name}</td>
            <td>${user.email}</td>
            <td>
                <span class="badge bg-${getRoleBadgeClass(user.role)}">
                    ${user.role}
                </span>
            </td>
            <td>
                <span class="badge bg-${user.is_active ? 'success' : 'danger'}">
                    ${user.is_active ? 'Aktywny' : 'Nieaktywny'}
                </span>
            </td>
            <td>${formatDate(user.last_login)}</td>
            <td class="text-end">
                <button class="btn btn-sm btn-outline-primary btn-action" onclick="editUser(${user.id})" title="Edytuj">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-outline-warning btn-action" onclick="resetPassword(${user.id})" title="Reset hasła">
                    <i class="bi bi-key"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger btn-action" onclick="deleteUser(${user.id})" title="Usuń">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function filterUsers(params = {}) {
    try {
        const searchInput = document.getElementById('searchInput');
        const activeOnlyCheckbox = document.getElementById('activeOnly');
        const sortSelect = document.getElementById('sortBy');

        const queryParams = new URLSearchParams({
            search: searchInput ? searchInput.value : '',
            active_only: activeOnlyCheckbox ? activeOnlyCheckbox.checked : true,
            sort: sortSelect ? sortSelect.value : 'display_name',
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

function getRoleBadgeClass(role) {
    switch (role.toLowerCase()) {
        case 'admin':
            return 'primary';
        case 'pm':
            return 'success';
        default:
            return 'secondary';
    }
}

function formatDate(timestamp) {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleString('pl-PL');
}

async function editUser(userId) {
    try {
        const response = await fetch(`/api/admin/users/${userId}`);
        const user = await response.json();
        
        if (!response.ok) {
            throw new Error(user.error || 'Błąd podczas ładowania danych użytkownika');
        }
        
        document.getElementById('userId').value = user.id;
        document.getElementById('userName').value = user.user_name;
        document.getElementById('userEmail').value = user.email;
        document.getElementById('userRole').value = user.role;
        document.getElementById('userActive').checked = user.is_active;
        
        // Ukryj pole hasła przy edycji
        document.querySelector('.password-field').style.display = 'none';
        document.getElementById('userPassword').required = false;
        
        document.getElementById('userModalTitle').textContent = 'Edytuj użytkownika';
        const userModal = new bootstrap.Modal(document.getElementById('userModal'));
        userModal.show();
        
    } catch (error) {
        console.error('Error loading user:', error);
        showError('Błąd podczas ładowania danych użytkownika');
    }
}

async function saveUser() {
    try {
        const userId = document.getElementById('userId').value;
        const userData = {
            user_name: document.getElementById('userName').value,
            email: document.getElementById('userEmail').value,
            role: document.getElementById('userRole').value,
            is_active: document.getElementById('userActive').checked
        };
        
        if (!userId) { // Nowy użytkownik
            userData.password = document.getElementById('userPassword').value;
        }
        
        const response = await fetch(`/api/admin/users${userId ? `/${userId}` : ''}`, {
            method: userId ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Błąd podczas zapisywania użytkownika');
        }
        
        bootstrap.Modal.getInstance(document.getElementById('userModal')).hide();
        showSuccess('Użytkownik został zapisany');
        loadUsers();
        
    } catch (error) {
        console.error('Error saving user:', error);
        showError('Błąd podczas zapisywania użytkownika');
    }
}

async function deleteUser(userId) {
    const user = users.find(u => u.id === userId);
    if (!user) return;
    
    document.getElementById('confirmMessage').textContent = 
        `Czy na pewno chcesz usunąć użytkownika "${user.user_name}"?`;
    
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    confirmModal.show();
    
    document.getElementById('confirmButton').onclick = async () => {
        try {
            const response = await fetch(`/api/admin/users/${userId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Błąd podczas usuwania użytkownika');
            }
            
            confirmModal.hide();
            showSuccess('Użytkownik został usunięty');
            loadUsers();
            
        } catch (error) {
            console.error('Error deleting user:', error);
            showError('Błąd podczas usuwania użytkownika');
        }
    };
}

async function resetPassword(userId) {
    const user = users.find(u => u.id === userId);
    if (!user) return;
    
    document.getElementById('confirmMessage').textContent = 
        `Czy na pewno chcesz zresetować hasło dla użytkownika "${user.user_name}"?`;
    
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    confirmModal.show();
    
    document.getElementById('confirmButton').onclick = async () => {
        try {
            const response = await fetch(`/api/admin/users/${userId}/reset-password`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'Błąd podczas resetowania hasła');
            }
            
            confirmModal.hide();
            
            // Pokaż nowe hasło
            Swal.fire({
                title: 'Hasło zostało zresetowane',
                html: `Nowe hasło: <strong>${result.password}</strong>`,
                icon: 'success',
                confirmButtonText: 'Kopiuj i zamknij',
                didOpen: () => {
                    // Zaznacz hasło do skopiowania
                    const selection = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(document.querySelector('strong'));
                    selection.removeAllRanges();
                    selection.addRange(range);
                }
            });
            
        } catch (error) {
            console.error('Error resetting password:', error);
            showError('Błąd podczas resetowania hasła');
        }
    };
}

function togglePassword() {
    const passwordInput = document.getElementById('userPassword');
    const icon = document.querySelector('.btn-outline-secondary i');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    } else {
        passwordInput.type = 'password';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    }
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

// Kontynuacja w następnym kroku... 