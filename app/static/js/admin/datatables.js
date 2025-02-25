function initializeDataTable(tableSelector, options = {}) {
    const table = $(tableSelector);
    
    // Zniszcz istniejącą instancję i wyczyść tabelę
    if ($.fn.DataTable.isDataTable(table)) {
        const dt = table.DataTable();
        dt.destroy();
        table.find('tbody').empty();
    }
    
    // Domyślne opcje
    const defaultOptions = {
        destroy: true,
        pageLength: 10,
        lengthMenu: [[10, 25, 50, 100], [10, 25, 50, 100]],
        responsive: true,
        processing: true,
        searching: true,
        paging: true,
        info: true,
        language: {
            lengthMenu: '_MENU_ entries per page',
            search: 'Search:',
            info: 'Showing _START_ to _END_ of _TOTAL_ entries',
            infoEmpty: 'Showing 0 to 0 of 0 entries',
            infoFiltered: '(filtered from _MAX_ total entries)',
            paginate: {
                first: 'First',
                last: 'Last',
                next: 'Next',
                previous: 'Previous'
            }
        },
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        initComplete: function(settings, json) {
            // Usuń duplikaty kontrolek po inicjalizacji
            const wrapper = $(this).closest('.dataTables_wrapper');
            wrapper.find('.dataTables_length:gt(0)').remove();
            wrapper.find('.dataTables_filter:gt(0)').remove();
            wrapper.find('.dataTables_info:gt(0)').remove();
            wrapper.find('.dataTables_paginate:gt(0)').remove();
        }
    };

    // Połącz opcje
    const finalOptions = { ...defaultOptions, ...options };
    
    // Inicjalizuj i zwróć instancję DataTable
    return table.DataTable(finalOptions);
}

// Konfiguracja DataTables
$(document).ready(function() {
    $('.datatable').DataTable({
        language: {
            search: "Szukaj:",
            lengthMenu: "Pokaż _MENU_ wpisów",
            info: "Wyświetlanie od _START_ do _END_ z _TOTAL_ wpisów",
            infoEmpty: "Wyświetlanie 0 wpisów",
            infoFiltered: "(filtrowanie spośród _MAX_ wszystkich wpisów)",
            paginate: {
                first: "Pierwsza",
                previous: "Poprzednia",
                next: "Następna",
                last: "Ostatnia"
            }
        },
        pageLength: 25,
        responsive: true,
        order: [[0, 'desc']]
    });
}); 