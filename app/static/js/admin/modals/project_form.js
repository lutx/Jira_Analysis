const ProjectFormModal = {
    ...BaseFormModal,
    
    init() {
        BaseFormModal.init.call(this, 'projectFormModal', 'projectForm', {
            onSuccess: this.handleSuccess.bind(this),
            beforeSubmit: this.validateForm.bind(this)
        });
        
        // Add date range validation
        this.bindDateValidation();
    },
    
    bindDateValidation() {
        const startDate = this.form.querySelector('[name="start_date"]');
        const endDate = this.form.querySelector('[name="end_date"]');
        
        startDate.addEventListener('change', () => this.validateDates());
        endDate.addEventListener('change', () => this.validateDates());
    },
    
    validateDates() {
        const startDate = new Date(this.form.querySelector('[name="start_date"]').value);
        const endDate = new Date(this.form.querySelector('[name="end_date"]').value);
        
        if (endDate < startDate) {
            toastr.error('End date cannot be earlier than start date');
            return false;
        }
        return true;
    },
    
    validateForm(form) {
        return this.validateDates();
    },
    
    handleSuccess(data) {
        if (window.ProjectsTable) {
            window.ProjectsTable.refresh();
        }
        this.defaultSuccess(data);
    }
};

$(document).ready(() => {
    ProjectFormModal.init();
}); 