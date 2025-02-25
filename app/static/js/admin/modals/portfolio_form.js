const PortfolioFormModal = {
    ...BaseFormModal,
    
    init() {
        BaseFormModal.init.call(this, 'portfolioFormModal', 'portfolioForm', {
            onSuccess: this.handleSuccess.bind(this),
            beforeSubmit: this.validateForm.bind(this)
        });
    },
    
    validateForm(form) {
        const projects = $(form).find('[name="projects"]').val();
        const manager = form.querySelector('[name="manager"]').value;
        
        if (!manager && projects.length > 0) {
            toastr.error('Portfolio must have a manager if it contains projects');
            return false;
        }
        return true;
    },
    
    handleSuccess(data) {
        if (window.PortfoliosTable) {
            window.PortfoliosTable.refresh();
        }
        this.defaultSuccess(data);
    }
};

$(document).ready(() => {
    PortfolioFormModal.init();
}); 