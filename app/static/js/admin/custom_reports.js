document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTables
    const reportTable = $('#reportTable').DataTable({
        pageLength: 25,
        dom: 'Bfrtip',
        buttons: ['copy', 'excel', 'pdf', 'csv']
    });
    
    const savedReportsTable = $('#savedReportsTable').DataTable({
        pageLength: 10
    });
    
    // Initialize DateRangePicker
    $('.daterange').daterangepicker({
        opens: 'left',
        locale: {
            format: 'YYYY-MM-DD'
        },
        ranges: {
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        }
    });
    
    // Handle report type change
    $('#reportType').on('change', function() {
        updateMetricsOptions(this.value);
        updateFilterFields(this.value);
    });
    
    // Initialize with default report type
    updateMetricsOptions($('#reportType').val());
    updateFilterFields($('#reportType').val());
    
    // Handle add filter button
    $('#addFilter').on('click', addFilterRow);
    
    // Handle report builder form submit
    $('#reportBuilder').on('submit', function(e) {
        e.preventDefault();
        generateReport();
    });
});

function updateMetricsOptions(reportType) {
    const metricsContainer = $('#metricsContainer');
    metricsContainer.empty();
    
    const metrics = getMetricsForType(reportType);
    metrics.forEach(metric => {
        metricsContainer.append(`
            <div class="col-md-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="metrics[]" 
                           value="${metric.value}" id="metric_${metric.value}">
                    <label class="form-check-label" for="metric_${metric.value}">
                        ${metric.label}
                    </label>
                </div>
            </div>
        `);
    });
}

function getMetricsForType(reportType) {
    const metricsByType = {
        workload: [
            { value: 'total_hours', label: 'Total Hours' },
            { value: 'avg_daily_hours', label: 'Average Daily Hours' },
            { value: 'utilization', label: 'Utilization' }
        ],
        roles: [
            { value: 'role_count', label: 'Role Count' },
            { value: 'role_distribution', label: 'Role Distribution' },
            { value: 'role_changes', label: 'Role Changes' }
        ],
        // Add more metric options for other report types
    };
    return metricsByType[reportType] || [];
}

function updateFilterFields(reportType) {
    const filterFields = $('.filter-field');
    filterFields.empty();
    
    const fields = getFieldsForType(reportType);
    fields.forEach(field => {
        filterFields.append(`<option value="${field.value}">${field.label}</option>`);
    });
}

function getFieldsForType(reportType) {
    const fieldsByType = {
        workload: [
            { value: 'user', label: 'User' },
            { value: 'team', label: 'Team' },
            { value: 'hours', label: 'Hours' }
        ],
        roles: [
            { value: 'role', label: 'Role' },
            { value: 'user_count', label: 'User Count' },
            { value: 'team', label: 'Team' }
        ],
        // Add more fields for other report types
    };
    return fieldsByType[reportType] || [];
}

function addFilterRow() {
    const newRow = $('.filter-row').first().clone();
    newRow.find('input').val('');
    newRow.find('select').prop('selectedIndex', 0);
    $('#filtersContainer').append(newRow);
}

function generateReport() {
    const formData = new FormData($('#reportBuilder')[0]);
    const filters = [];
    
    // Collect filter data
    $('.filter-row').each(function() {
        const field = $(this).find('.filter-field').val();
        const operator = $(this).find('.filter-operator').val();
        const value = $(this).find('.filter-value').val();
        
        if (field && operator && value) {
            filters.push({ field, operator, value });
        }
    });
    
    const reportData = {
        type: formData.get('report_type'),
        date_range: formData.get('date_range'),
        group_by: formData.get('group_by'),
        metrics: formData.getAll('metrics[]'),
        filters: filters
    };
    
    fetch('/admin/reports/custom/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify(reportData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            displayReportResults(data.results);
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error generating report:', error);
        showNotification('Error generating report', 'error');
    });
}

function displayReportResults(results) {
    // Show results section
    $('#reportResults').removeClass('d-none');
    
    // Update charts
    updateChart(
        document.querySelector('[data-chart-id="primary"]'),
        results.primary_chart
    );
    updateChart(
        document.querySelector('[data-chart-id="secondary"]'),
        results.secondary_chart
    );
    
    // Update table
    const table = $('#reportTable').DataTable();
    table.clear();
    
    // Set headers
    const headers = results.columns.map(col => col.label);
    table.columns().header().toJQuery().each(function(i) {
        $(this).html(headers[i] || '');
    });
    
    // Add data
    results.data.forEach(row => {
        table.row.add(row);
    });
    
    table.draw();
}

function saveReport() {
    $('#saveReportModal').modal('show');
}

function submitSaveReport() {
    const formData = new FormData($('#saveReportForm')[0]);
    const reportConfig = {
        name: formData.get('report_name'),
        description: formData.get('description'),
        is_public: formData.get('is_public') === 'on',
        config: {
            type: $('#reportType').val(),
            date_range: $('[name=date_range]').val(),
            group_by: $('[name=group_by]').val(),
            metrics: $('[name="metrics[]"]:checked').map(function() {
                return this.value;
            }).get(),
            filters: $('.filter-row').map(function() {
                return {
                    field: $(this).find('.filter-field').val(),
                    operator: $(this).find('.filter-operator').val(),
                    value: $(this).find('.filter-value').val()
                };
            }).get()
        }
    };
    
    fetch('/admin/reports/custom/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify(reportConfig)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            $('#saveReportModal').modal('hide');
            showNotification('Report saved successfully', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving report:', error);
        showNotification('Error saving report', 'error');
    });
}

function loadReport(reportId) {
    fetch(`/admin/reports/custom/${reportId}`)
        .then(response => response.json())
        .then(report => {
            // Set form values
            $('#reportType').val(report.config.type).trigger('change');
            $('[name=date_range]').val(report.config.date_range);
            $('[name=group_by]').val(report.config.group_by);
            
            // Set metrics
            report.config.metrics.forEach(metric => {
                $(`#metric_${metric}`).prop('checked', true);
            });
            
            // Set filters
            $('#filtersContainer').empty();
            report.config.filters.forEach(filter => {
                const row = $('.filter-row').first().clone();
                row.find('.filter-field').val(filter.field);
                row.find('.filter-operator').val(filter.operator);
                row.find('.filter-value').val(filter.value);
                $('#filtersContainer').append(row);
            });
            
            // Generate report
            generateReport();
        })
        .catch(error => {
            console.error('Error loading report:', error);
            showNotification('Error loading report', 'error');
        });
}

function runReport(reportId) {
    fetch(`/admin/reports/custom/${reportId}/run`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayReportResults(data.results);
            } else {
                showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error running report:', error);
            showNotification('Error running report', 'error');
        });
}

function deleteReport(reportId) {
    if (confirm('Are you sure you want to delete this report?')) {
        fetch(`/admin/reports/custom/${reportId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                showNotification('Report deleted successfully', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(result.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting report:', error);
            showNotification('Error deleting report', 'error');
        });
    }
}

function exportReport(format) {
    const reportId = $('#reportResults').data('report-id');
    window.location.href = `/admin/reports/custom/${reportId}/export/${format}`;
} 