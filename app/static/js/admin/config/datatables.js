$.extend(true, $.fn.dataTable.defaults, {
    processing: true,
    serverSide: true,
    pageLength: 25,
    dom: 'Bfrtip',
    buttons: ['copy', 'csv', 'excel', 'pdf'],
    language: {
        processing: '<div class="spinner-border text-primary"></div>',
        search: "Search:",
        lengthMenu: "Show _MENU_ entries",
        info: "Showing _START_ to _END_ of _TOTAL_ entries",
        infoEmpty: "Showing 0 to 0 of 0 entries",
        infoFiltered: "(filtered from _MAX_ total entries)",
        paginate: {
            first: "First",
            last: "Last",
            next: "Next",
            previous: "Previous"
        }
    }
}); 