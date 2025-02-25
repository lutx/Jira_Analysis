const WorklogFormModal = {
    ...BaseFormModal,
    
    init() {
        BaseFormModal.init.call(this, 'worklogFormModal', 'worklogForm', {
            onSuccess: this.handleSuccess.bind(this),
            beforeSubmit: this.validateForm.bind(this)
        });
    },
    
    validateForm(form) {
        const hours = parseFloat(form.querySelector('[name="hours"]').value);
        if (hours <= 0 || hours > 24) {
            toastr.error('Hours must be between 0 and 24');
            return false;
        }
        return true;
    },
    
    handleSuccess(data) {
        if (window.WorklogsTable) {
            window.WorklogsTable.refresh();
        }
        this.defaultSuccess(data);
    }
};

$(document).ready(() => {
    WorklogFormModal.init();
}); 