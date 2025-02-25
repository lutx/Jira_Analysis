// Sprawdź, czy instancja już istnieje
if (typeof window.adminModals === 'undefined') {
    class AdminModals {
        constructor() {
            // Sprawdź czy elementy istnieją przed inicjalizacją
            this.confirmationModal = document.getElementById('confirmationModal') ? 
                new bootstrap.Modal(document.getElementById('confirmationModal')) : null;
                
            this.formModal = document.getElementById('formModal') ? 
                new bootstrap.Modal(document.getElementById('formModal')) : null;
                
            this.loadingModal = document.getElementById('loadingModal') ? 
                new bootstrap.Modal(document.getElementById('loadingModal'), {
                    backdrop: 'static',
                    keyboard: false
                }) : null;
                
            this.errorModal = document.getElementById('errorModal') ? 
                new bootstrap.Modal(document.getElementById('errorModal')) : null;

            this.initializeEventListeners();
        }

        initializeEventListeners() {
            // Sprawdź czy element istnieje przed dodaniem listenera
            const formModalElement = document.getElementById('formModal');
            if (formModalElement) {
                formModalElement.addEventListener('hidden.bs.modal', () => {
                    const form = document.getElementById('genericForm');
                    if (form) form.reset();
                    
                    const formFields = document.getElementById('formFields');
                    if (formFields) formFields.innerHTML = '';
                });
            }
        }

        // Confirmation Modal
        showConfirmation(message, callback) {
            if (!this.confirmationModal) return;
            
            const messageElement = document.getElementById('confirmationMessage');
            if (messageElement) messageElement.textContent = message;
            
            const confirmBtn = document.getElementById('confirmActionBtn');
            if (confirmBtn) {
                confirmBtn.onclick = () => {
                    this.confirmationModal.hide();
                    callback();
                };
            }
            
            this.confirmationModal.show();
        }

        // Form Modal
        showForm(title, fields, callback) {
            if (!this.formModal) return;
            
            const titleElement = document.querySelector('#formModal .modal-title');
            if (titleElement) titleElement.textContent = title;
            
            const formFields = document.getElementById('formFields');
            formFields.innerHTML = '';
            
            fields.forEach(field => {
                const div = document.createElement('div');
                div.className = 'mb-3';
                
                const label = document.createElement('label');
                label.className = 'form-label';
                label.textContent = field.label;
                
                let input;
                if (field.type === 'select') {
                    input = document.createElement('select');
                    input.multiple = field.multiple || false;
                    input.className = 'form-control select2';
                    
                    if (field.options) {
                        field.options.forEach(option => {
                            const opt = document.createElement('option');
                            opt.value = option.value;
                            opt.textContent = option.label;
                            if (field.value && field.value.includes(option.value)) {
                                opt.selected = true;
                            }
                            input.appendChild(opt);
                        });
                    }
                    
                    // Inicjalizuj Select2 po dodaniu do DOM
                    setTimeout(() => {
                        $(input).select2({
                            theme: 'bootstrap4',
                            placeholder: field.placeholder || 'Select options',
                            width: '100%',
                            dropdownParent: $('#formModal'),
                            closeOnSelect: false
                        });
                    }, 0);
                } else {
                    input = document.createElement('input');
                    input.type = field.type || 'text';
                    if (field.value) input.value = field.value;
                    input.className = 'form-control';
                }
                
                input.name = field.name;
                if (field.required) input.required = true;
                
                div.appendChild(label);
                div.appendChild(input);
                formFields.appendChild(div);
            });
            
            this.formModal._element.addEventListener('hidden.bs.modal', () => {
                $('.select2-hidden-accessible').select2('destroy');
            });
            
            document.getElementById('saveFormBtn').onclick = () => {
                const formData = new FormData(document.getElementById('genericForm'));
                const data = Object.fromEntries(formData);
                callback(data);
            };
            
            this.formModal.show();
        }

        // Loading Modal
        showLoading(message = 'Loading...') {
            if (!this.loadingModal) return;
            
            const messageElement = document.getElementById('loadingMessage');
            if (messageElement) messageElement.textContent = message;
            
            this.loadingModal.show();
        }

        hideLoading() {
            if (!this.loadingModal) return;
            this.loadingModal.hide();
        }

        // Error Modal
        showError(message) {
            if (!this.errorModal) return;
            
            const messageElement = document.getElementById('errorMessage');
            if (messageElement) messageElement.textContent = message;
            
            this.errorModal.show();
        }
    }

    // Utwórz pojedynczą instancję
    window.adminModals = new AdminModals();
}

// Obsługa modali
$(document).ready(function() {
    // Inicjalizacja wszystkich modali
    $('.modal').modal({
        backdrop: 'static',
        keyboard: false,
        show: false
    });

    // Czyszczenie formularza przy zamknięciu modala
    $('.modal').on('hidden.bs.modal', function() {
        $(this).find('form').trigger('reset');
        $(this).find('.is-invalid').removeClass('is-invalid');
        $(this).find('.invalid-feedback').remove();
    });

    // Obsługa przycisków otwierających modale
    $('[data-toggle="modal"]').on('click', function() {
        const target = $(this).data('target');
        $(target).modal('show');
    });
}); 