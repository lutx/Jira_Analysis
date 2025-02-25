async function logout() {
    try {
        // Usuń token z localStorage
        localStorage.removeItem('token');
        
        const response = await fetch('/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            window.location.href = '/login';
        } else {
            console.error('Błąd podczas wylogowywania');
        }
    } catch (error) {
        console.error('Błąd:', error);
        alert('Błąd połączenia z serwerem');
    }
}

// Dodaj token do każdego żądania
function addAuthHeader(headers = {}) {
    const token = localStorage.getItem('token');
    if (token) {
        return {
            ...headers,
            'Authorization': `Bearer ${token}`
        };
    }
    return headers;
}

// Wspólna obsługa błędów
function handleError(error, customMessage = 'Błąd połączenia z serwerem') {
    console.error('Błąd:', error);
    alert(customMessage);
}

// Użycie
try {
    // kod
} catch (error) {
    handleError(error);
}

// Pokaż/ukryj wskaźnik ładowania
function showLoading() {
    const loading = document.createElement('div');
    loading.className = 'loading';
    loading.innerHTML = `
        <div class="spinner-border loading-spinner text-primary" role="status">
            <span class="visually-hidden">Ładowanie...</span>
        </div>
    `;
    document.body.appendChild(loading);
}

function hideLoading() {
    const loading = document.querySelector('.loading');
    if (loading) {
        loading.remove();
    }
}

// Flash messages
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        });
    }, 5000);

    // Enable tooltips
    $('[data-toggle="tooltip"]').tooltip();

    // Enable popovers
    $('[data-toggle="popover"]').popover();

    // CSRF token for AJAX requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
    
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrfToken);
            }
        }
    });

    // Usuń skrypt Font Awesome Kit jeśli istnieje
    const faScript = document.querySelector('script[src*="kit.fontawesome.com"]');
    if (faScript) {
        faScript.remove();
    }
});

// Confirmation dialog
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Form validation
function validateForm(form) {
    let isValid = true;
    form.querySelectorAll('[required]').forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('is-invalid');
        } else {
            input.classList.remove('is-invalid');
        }
    });
    return isValid;
}

// Obsługa błędów
function handleError(error) {
    console.error(error);
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show';
    alert.innerHTML = `
        <strong>Błąd!</strong> ${error.message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('main').prepend(alert);
}

// Inicjalizacja wszystkich dropdownów Bootstrap
document.addEventListener('DOMContentLoaded', function() {
    var dropdownElementList = [].slice.call(document.querySelectorAll('.dropdown-toggle'))
    var dropdownList = dropdownElementList.map(function (dropdownToggleEl) {
        return new bootstrap.Dropdown(dropdownToggleEl)
    })
});

// Inicjalizacja Select2 dla wszystkich select z klasą .select2
document.addEventListener('DOMContentLoaded', function() {
    if ($.fn.select2) {
        $('.select2').select2({
            width: '100%',
            placeholder: 'Wybierz...',
            allowClear: true
        });
    }
});

// Dodaj token CSRF do każdego żądania AJAX
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", $('meta[name="csrf-token"]').attr('content'));
        }
    }
});

// Upewnij się, że jQuery jest załadowane
if (typeof jQuery === 'undefined') {
    console.error('jQuery is not loaded');
} else {
    (function($) {
        'use strict';

        // Funkcja do pobierania tokenu CSRF
        function getCsrfToken() {
            return document.querySelector('meta[name="csrf-token"]')?.content || 
                   document.querySelector('input[name="csrf_token"]')?.value;
        }

        // Konfiguracja globalna AJAX
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    const token = getCsrfToken();
                    if (token) {
                        xhr.setRequestHeader("X-CSRFToken", token);
                    }
                }
            }
        });

        // Obsługa formularzy AJAX
        $(document).ready(function() {
            $('form[data-ajax]').on('submit', function(e) {
                e.preventDefault();
                var $form = $(this);
                
                const data = new FormData($form[0]);
                
                $.ajax({
                    url: $form.attr('action'),
                    method: $form.attr('method'),
                    data: data,
                    processData: false,
                    contentType: false,
                    beforeSend: function(xhr) {
                        $form.find('[type="submit"]').prop('disabled', true);
                        const token = getCsrfToken();
                        if (token) {
                            xhr.setRequestHeader("X-CSRFToken", token);
                        }
                    },
                    success: function(response) {
                        if (response.redirect) {
                            window.location.href = response.redirect;
                        }
                        if (response.message) {
                            showNotification(response.message, response.status || 'success');
                        }
                    },
                    error: function(xhr) {
                        showNotification(
                            xhr.responseJSON?.message || 'Wystąpił błąd',
                            'error'
                        );
                    },
                    complete: function() {
                        $form.find('[type="submit"]').prop('disabled', false);
                    }
                });
            });

            // Inicjalizacja tooltipów
            var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function(tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        });

        // Funkcja do wyświetlania powiadomień
        window.showNotification = function(message, type = 'info') {
            const toast = `
                <div class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="toast-header bg-${type}">
                        <strong class="me-auto text-white">Powiadomienie</strong>
                        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                    <div class="toast-body">
                        ${message}
                    </div>
                </div>
            `;
            
            const toastContainer = document.getElementById('toast-container');
            if (toastContainer) {
                toastContainer.insertAdjacentHTML('beforeend', toast);
                const toastElement = toastContainer.lastElementChild;
                const bsToast = new bootstrap.Toast(toastElement);
                bsToast.show();
            }
        };
    })(jQuery);
} 