const TeamFormModal = {
    ...BaseFormModal,
    
    init() {
        BaseFormModal.init.call(this, 'teamFormModal', 'teamForm', {
            onSuccess: this.handleSuccess.bind(this),
            beforeSubmit: this.validateForm.bind(this)
        });
    },
    
    validateForm(form) {
        const leader = form.querySelector('[name="leader"]').value;
        const members = $(form).find('[name="members"]').val();
        
        if (!leader && members.length > 0) {
            toastr.error('Team must have a leader if it has members');
            return false;
        }
        
        return true;
    },
    
    handleSuccess(data) {
        // Refresh teams table if exists
        if (window.TeamsTable) {
            window.TeamsTable.refresh();
        }
        
        // Call default success handler
        this.defaultSuccess(data);
    }
};

// Initialize on document ready
$(document).ready(() => {
    TeamFormModal.init();
}); 