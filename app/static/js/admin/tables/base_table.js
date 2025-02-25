const BaseTable = {
    init(tableId, options = {}) {
        const defaultOptions = {
            processing: true,
            serverSide: true,
            pageLength: 25,
            dom: 'Bfrtip',
            buttons: ['copy', 'csv', 'excel', 'pdf'],
            ajax: {
                url: options.url,
                type: 'GET',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                }
            }
        };

        this.table = $(`#${tableId}`).DataTable({
            ...defaultOptions,
            ...options
        });

        this.bindEvents();
    },

    bindEvents() {
        // Implementacja w klasach pochodnych
    },

    refresh() {
        this.table.ajax.reload();
    },

    destroy() {
        if (this.table) {
            this.table.destroy();
        }
    }
}; 