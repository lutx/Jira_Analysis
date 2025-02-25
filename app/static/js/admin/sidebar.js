document.addEventListener('DOMContentLoaded', function() {
    // Poprawiona obsługa menu bocznego
    class SidebarManager {
        constructor() {
            this.sidebar = document.querySelector('.sidebar');
            this.sidebarToggle = document.querySelector('.sidebar-toggle');
            this.activeSubmenu = null;
            this.initializeEventListeners();
            this.initializeResponsiveBehavior();
        }

        initializeEventListeners() {
            // Poprawiona obsługa submenu
            const submenuToggles = document.querySelectorAll('.submenu-toggle');
            submenuToggles.forEach(toggle => {
                toggle.addEventListener('click', (e) => this.handleSubmenuToggle(e));
            });

            // Poprawiona obsługa toggle na mobile
            if (this.sidebarToggle) {
                this.sidebarToggle.addEventListener('click', () => this.toggleSidebar());
            }

            // Zamykanie przy kliknięciu poza
            document.addEventListener('click', (e) => this.handleOutsideClick(e));
        }

        initializeResponsiveBehavior() {
            // Responsywne zachowanie
            const mediaQuery = window.matchMedia('(max-width: 768px)');
            mediaQuery.addListener(() => this.handleResponsiveChange());
            this.handleResponsiveChange(mediaQuery);
        }

        handleSubmenuToggle(e) {
            e.preventDefault();
            const submenu = e.target.nextElementSibling;
            
            if (this.activeSubmenu && this.activeSubmenu !== submenu) {
                this.activeSubmenu.classList.remove('show');
            }
            
            submenu.classList.toggle('show');
            this.activeSubmenu = submenu;
        }

        toggleSidebar() {
            this.sidebar.classList.toggle('show');
            document.body.classList.toggle('sidebar-open');
        }

        handleOutsideClick(e) {
            if (window.innerWidth <= 768 && 
                this.sidebar.classList.contains('show') && 
                !this.sidebar.contains(e.target) && 
                !this.sidebarToggle.contains(e.target)) {
                this.toggleSidebar();
            }
        }

        handleResponsiveChange(e) {
            if (e.matches) {
                this.sidebar.classList.remove('show');
                document.body.classList.remove('sidebar-open');
            }
        }
    }

    // Inicjalizacja
    const sidebarManager = new SidebarManager();
}); 