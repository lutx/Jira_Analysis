document.addEventListener('DOMContentLoaded', function() {
    // Inicjalizacja tooltipów Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Inicjalizacja tabel DataTables
    const tables = document.querySelectorAll('.datatable');
    tables.forEach(table => {
        new DataTable(table, {
            language: {
                url: '//cdn.datatables.net/plug-ins/1.10.24/i18n/Polish.json'
            }
        });
    });
}); 