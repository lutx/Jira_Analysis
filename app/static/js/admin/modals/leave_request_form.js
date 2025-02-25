const LeaveRequestFormModal = {
    ...BaseFormModal,
    
    init() {
        BaseFormModal.init.call(this, 'leaveRequestFormModal', 'leaveRequestForm', {
            onSuccess: this.handleSuccess.bind(this),
            beforeSubmit: this.validateForm.bind(this)
        });
        
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
        if (!this.validateDates()) {
            return false;
        }
        
        const substitute = form.querySelector('[name="substitute"]').value;
        if (!substitute) {
            toastr.error('Please select a substitute');
            return false;
        }
        
        return true;
    },
    
    handleSuccess(data) {
        if (window.LeaveRequestsTable) {
            window.LeaveRequestsTable.refresh();
        }
        this.defaultSuccess(data);
    }
};

$(document).ready(() => {
    LeaveRequestFormModal.init();
}); 