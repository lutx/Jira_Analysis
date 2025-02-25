const RolesTable = {
    ...BaseTable,
    
    init() {
        BaseTable.init.call(this, 'rolesTable', {
            ajax: '/api/admin/roles',
            columns: [
                { data: 'name' },
                { data: 'description' },
                { data: 'permissions' },
                { 
                    data: 'id',
                    render: (data, type, row) => this.renderActions(data)
                }
            ]
        });
    },
    
    renderActions(id) {
        return `
            <button class="btn btn-sm btn-info" onclick="editRole(${id})">
                <i class="fas fa-edit"></i>
            </button>
            <button class="btn btn-sm btn-danger" onclick="deleteRole(${id})">
                <i class="fas fa-trash"></i>
            </button>
        `;
    }
};

// Make it globally available
window.RolesTable = RolesTable;

$(document).ready(() => {
    RolesTable.init();
}); 