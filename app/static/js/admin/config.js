const AdminConfig = {
    // API endpoints
    api: {
        base: '/api',
        users: '/api/users',
        roles: '/api/roles',
        worklogs: '/api/worklogs',
        settings: '/api/settings',
        jira: '/api/jira'
    },

    // UI configuration
    ui: {
        theme: 'light',
        sidebarWidth: 250,
        animationDuration: 300,
        toastDuration: 3000
    },

    // DataTables default configuration
    datatables: {
        pageLength: 25,
        responsive: true,
        language: {
            search: "Szukaj:",
            lengthMenu: "Pokaż _MENU_ wpisów",
            info: "Wyświetlanie od _START_ do _END_ z _TOTAL_ wpisów"
        }
    },

    // Form validation messages
    validation: {
        required: "To pole jest wymagane",
        email: "Wprowadź poprawny adres email",
        minLength: "Minimalna długość to {0} znaków",
        maxLength: "Maksymalna długość to {0} znaków"
    }
}; 