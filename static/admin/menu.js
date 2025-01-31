const adminMenu = [
    {
        title: 'Dashboard',
        url: '/admin/dashboard',
        icon: 'bi-speedometer2',
        roles: ['admin', 'superadmin']
    },
    {
        title: 'Użytkownicy Jira',
        url: '/admin/users',
        icon: 'bi-people-fill',
        roles: ['admin', 'superadmin']
    },
    {
        title: 'Portfolia',
        url: '/admin/portfolios',
        icon: 'bi-folder2',
        roles: ['admin', 'superadmin']
    },
    {
        title: 'Ustawienia',
        url: '/admin/settings',
        icon: 'bi-gear',
        roles: ['superadmin']
    }
];

// Funkcja pobierająca rolę użytkownika
async function getUserRole() {
    try {
        const response = await fetch('/api/auth/user-role');
        const data = await response.json();
        return data.role;
    } catch (error) {
        console.error('Error getting user role:', error);
        return null;
    }
}

// Funkcja renderująca menu
async function renderAdminMenu() {
    const menuContainer = document.getElementById('adminMenu');
    if (!menuContainer) return;

    try {
        const userRole = await getUserRole();
        if (!userRole) return;

        const menuHTML = adminMenu
            .filter(item => item.roles.includes(userRole))
            .map(item => `
                <li class="nav-item">
                    <a class="nav-link ${window.location.pathname === item.url ? 'active' : ''}" 
                       href="${item.url}">
                        <i class="bi ${item.icon}"></i>
                        <span class="ms-2">${item.title}</span>
                    </a>
                </li>
            `)
            .join('');
        
        menuContainer.innerHTML = menuHTML;
    } catch (error) {
        console.error('Error rendering admin menu:', error);
    }
}

// Wywołaj funkcję przy załadowaniu strony
document.addEventListener('DOMContentLoaded', renderAdminMenu); 