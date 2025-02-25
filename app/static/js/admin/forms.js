// Inicjalizacja formularzy
$(document).ready(function() {
    // Inicjalizacja Select2
    $('.select2').select2({
        theme: 'bootstrap4',
        width: '100%'
    });

    // Inicjalizacja DatePicker
    $('.datepicker').datepicker({
        format: 'yyyy-mm-dd',
        autoclose: true,
        todayHighlight: true
    });

    // Walidacja formularzy przed wysłaniem
    $('form').on('submit', function(e) {
        const form = $(this);
        if (!form[0].checkValidity()) {
            e.preventDefault();
            e.stopPropagation();
        }
        form.addClass('was-validated');
    });

    // Obsługa dynamicznych formularzy
    $('.dynamic-form-add').on('click', function() {
        const template = $(this).data('template');
        const container = $(this).data('container');
        $(container).append($(template).html());
    });

    $('.dynamic-form-remove').on('click', function() {
        $(this).closest('.dynamic-form-item').remove();
    });
}); 