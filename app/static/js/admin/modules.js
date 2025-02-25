// Moduł zarządzania administracją
const AdminModule = (function() {
    // Prywatne zmienne
    let config = {
        apiEndpoints: {
            users: '/api/users',
            roles: '/api/roles',
            worklogs: '/api/worklogs',
            settings: '/api/settings'
        },
        refreshInterval: 5000
    };

    // Cache dla selektorów DOM
    const domElements = {
        sidebar: '.sidebar',
        content: '.admin-content',
        modals: '.modal',
        forms: 'form',
        tables: '.datatable'
    };

    // Inicjalizacja modułu
    function init(userConfig = {}) {
        config = { ...config, ...userConfig };
        initializeComponents();
        setupEventListeners();
    }

    // Inicjalizacja komponentów
    function initializeComponents() {
        initializeTables();
        initializeModals();
        initializeForms();
        initializeTooltips();
    }

    // Obsługa tabel
    function initializeTables() {
        $(domElements.tables).each(function() {
            const tableConfig = $(this).data('config') || {};
            initializeDataTable(this, tableConfig);
        });
    }

    // Obsługa formularzy
    function initializeForms() {
        $(domElements.forms).each(function() {
            const form = $(this);
            form.on('submit', handleFormSubmit);
        });
    }

    // Obsługa modali
    function initializeModals() {
        $(domElements.modals).each(function() {
            const modal = new bootstrap.Modal(this, {
                backdrop: 'static',
                keyboard: false
            });
            
            $(this).on('hidden.bs.modal', function() {
                resetForm(this);
            });
        });
    }

    // API
    return {
        init,
        config,
        refreshData: initializeComponents
    };
})();

// Inicjalizacja po załadowaniu dokumentu
document.addEventListener('DOMContentLoaded', function() {
    AdminModule.init();
}); 