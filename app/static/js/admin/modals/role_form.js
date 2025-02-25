const RoleFormModal = {
    ...BaseFormModal,
    
    init() {
        BaseFormModal.init.call(this, 'roleFormModal', 'roleForm', {
            onSuccess: this.handleSuccess.bind(this)
        });
    },
    
    handleSuccess(data) {
        // Refresh roles table if exists
        if (window.RolesTable) {
            window.RolesTable.refresh();
        }
        
        // Call default success handler
        this.defaultSuccess(data);
    }
};

// Initialize on document ready
$(document).ready(() => {
    RoleFormModal.init();
}); 