const BaseFormModal = {
    init(modalId, formId, options = {}) {
        this.modal = document.getElementById(modalId);
        this.form = document.getElementById(formId);
        this.options = {
            onSuccess: options.onSuccess || this.defaultSuccess,
            onError: options.onError || this.defaultError,
            beforeSubmit: options.beforeSubmit || this.defaultBeforeSubmit,
            afterSubmit: options.afterSubmit || this.defaultAfterSubmit
        };
        
        this.bindEvents();
        this.initializePlugins();
    },

    bindEvents() {
        this.form.addEventListener('submit', this.handleSubmit.bind(this));
        $(this.modal).on('shown.bs.modal', this.handleModalShow.bind(this));
        $(this.modal).on('hidden.bs.modal', this.handleModalHide.bind(this));
    },

    initializePlugins() {
        // Initialize Select2
        $(this.form).find('.select2').select2({
            dropdownParent: $(this.modal)
        });

        // Initialize Datepicker
        $(this.form).find('.datepicker').datepicker({
            format: 'yyyy-mm-dd',
            autoclose: true
        });
    },

    async handleSubmit(e) {
        e.preventDefault();
        
        if (!await this.options.beforeSubmit(this.form)) {
            return;
        }

        const formData = new FormData(this.form);
        
        try {
            const response = await fetch(this.form.action, {
                method: this.form.method,
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                await this.options.onSuccess(data);
            } else {
                await this.options.onError(data);
            }
        } catch (error) {
            console.error('Form submission error:', error);
            toastr.error('An error occurred while submitting the form');
        }
        
        await this.options.afterSubmit(this.form);
    },

    handleModalShow() {
        // Reset form on show
        this.form.reset();
        
        // Reset Select2
        $(this.form).find('.select2').trigger('change');
    },

    handleModalHide() {
        // Clear validation errors
        $(this.form).find('.is-invalid').removeClass('is-invalid');
        $(this.form).find('.invalid-feedback').remove();
    },

    defaultSuccess(data) {
        toastr.success(data.message || 'Form submitted successfully');
        $(this.modal).modal('hide');
    },

    defaultError(data) {
        if (data.errors) {
            Object.entries(data.errors).forEach(([field, errors]) => {
                const input = this.form.querySelector(`[name="${field}"]`);
                if (input) {
                    input.classList.add('is-invalid');
                    const feedback = document.createElement('div');
                    feedback.className = 'invalid-feedback';
                    feedback.textContent = errors.join(', ');
                    input.parentNode.appendChild(feedback);
                }
            });
        }
        toastr.error(data.message || 'Error submitting form');
    },

    defaultBeforeSubmit() {
        return true;
    },

    defaultAfterSubmit() {
        // Default implementation does nothing
    }
}; 