document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const logsTable = $('#logsTable').DataTable({
        pageLength: 25,
        order: [[0, 'desc']],
        dom: 'Bfrtip',
        buttons: ['copy', 'csv', 'excel']
    });
    
    // Initialize DateRangePicker
    $('.daterange').daterangepicker({
        opens: 'left',
        locale: {
            format: 'YYYY-MM-DD'
        },
        ranges: {
            'Today': [moment(), moment()],
            'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        }
    });
    
    // Handle filter form submit
    $('#logFilters').on('submit', function(e) {
        e.preventDefault();
        updateLogs();
    });
});

function updateLogs() {
    const filters = {
        level: $('[name=level]').val(),
        date_range: $('[name=date_range]').val(),
        module: $('[name=module]').val()
    };
    
    fetch('/admin/logs/data?' + new URLSearchParams(filters))
        .then(response => response.json())
        .then(data => {
            // Update summary cards
            updateSummaryCards(data.summary);
            
            // Update logs table
            updateTable(data.logs);
        })
        .catch(error => {
            console.error('Error updating logs:', error);
            showNotification('Error updating logs', 'error');
        });
}

function updateSummaryCards(summary) {
    document.querySelector('.bg-info h3').textContent = summary.total_logs;
    document.querySelector('.bg-warning h3').textContent = summary.warning_count;
    document.querySelector('.bg-danger h3').textContent = summary.error_count;
    document.querySelector('.bg-success h3').textContent = summary.success_rate + '%';
}

function updateTable(logs) {
    const table = $('#logsTable').DataTable();
    table.clear();
    
    logs.forEach(log => {
        table.row.add([
            log.timestamp,
            `<span class="badge bg-${log.level_class}">${log.level}</span>`,
            log.module,
            log.message,
            log.details ? `
                <button class="btn btn-sm btn-info" onclick="viewLogDetails(${log.id})">
                    <i class="bi bi-info-circle"></i>
                </button>
            ` : ''
        ]);
    });
    
    table.draw();
}

function viewLogDetails(logId) {
    fetch(`/admin/logs/${logId}`)
        .then(response => response.json())
        .then(log => {
            const content = document.getElementById('logDetailsContent');
            content.innerHTML = `
                <div class="mb-3">
                    <h6>Timestamp</h6>
                    <p>${log.timestamp}</p>
                </div>
                
                <div class="mb-3">
                    <h6>Level</h6>
                    <p><span class="badge bg-${log.level_class}">${log.level}</span></p>
                </div>
                
                <div class="mb-3">
                    <h6>Module</h6>
                    <p>${log.module}</p>
                </div>
                
                <div class="mb-3">
                    <h6>Message</h6>
                    <p>${log.message}</p>
                </div>
                
                <div class="mb-3">
                    <h6>Stack Trace</h6>
                    <pre class="bg-light p-3"><code>${log.stack_trace || 'No stack trace available'}</code></pre>
                </div>
                
                <div class="mb-3">
                    <h6>Additional Data</h6>
                    <pre class="bg-light p-3"><code>${JSON.stringify(log.additional_data || {}, null, 2)}</code></pre>
                </div>
            `;
            
            $('#logDetailsModal').modal('show');
        })
        .catch(error => {
            console.error('Error loading log details:', error);
            showNotification('Error loading log details', 'error');
        });
}

function clearLogs() {
    if (confirm('Are you sure you want to clear all logs? This action cannot be undone.')) {
        fetch('/admin/logs/clear', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                showNotification('Logs cleared successfully', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(result.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error clearing logs:', error);
            showNotification('Error clearing logs', 'error');
        });
    }
}

function downloadLogs() {
    const filters = {
        level: $('[name=level]').val(),
        date_range: $('[name=date_range]').val(),
        module: $('[name=module]').val()
    };
    
    window.location.href = '/admin/logs/download?' + new URLSearchParams(filters);
} 