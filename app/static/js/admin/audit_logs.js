document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const auditTable = $('#auditTable').DataTable({
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
    $('#auditFilters').on('submit', function(e) {
        e.preventDefault();
        updateAuditLogs();
    });
});

function updateAuditLogs() {
    const filters = {
        action_type: $('[name=action_type]').val(),
        user_id: $('[name=user_id]').val(),
        date_range: $('[name=date_range]').val()
    };
    
    fetch('/admin/audit/data?' + new URLSearchParams(filters))
        .then(response => response.json())
        .then(data => {
            // Update summary cards
            updateSummaryCards(data.summary);
            
            // Update audit table
            updateTable(data.audit_entries);
        })
        .catch(error => {
            console.error('Error updating audit logs:', error);
            showNotification('Error updating audit logs', 'error');
        });
}

function updateSummaryCards(summary) {
    document.querySelector('.bg-primary h3').textContent = summary.total_actions;
    document.querySelector('.bg-info h3').textContent = summary.unique_users;
    document.querySelector('.bg-warning h3').textContent = summary.most_common_action;
    document.querySelector('.bg-success h3').textContent = summary.todays_actions;
}

function updateTable(entries) {
    const table = $('#auditTable').DataTable();
    table.clear();
    
    entries.forEach(entry => {
        table.row.add([
            entry.timestamp,
            entry.user.display_name,
            `<span class="badge bg-${entry.action_class}">${entry.action}</span>`,
            entry.resource,
            entry.ip_address,
            `<button class="btn btn-sm btn-info" onclick="viewAuditDetails(${entry.id})">
                <i class="bi bi-info-circle"></i>
            </button>`
        ]);
    });
    
    table.draw();
}

function viewAuditDetails(entryId) {
    fetch(`/admin/audit/${entryId}`)
        .then(response => response.json())
        .then(entry => {
            const content = document.getElementById('auditDetailsContent');
            content.innerHTML = `
                <div class="mb-3">
                    <h6>Timestamp</h6>
                    <p>${entry.timestamp}</p>
                </div>
                
                <div class="mb-3">
                    <h6>User</h6>
                    <p>${entry.user.display_name} (${entry.user.email})</p>
                </div>
                
                <div class="mb-3">
                    <h6>Action</h6>
                    <p><span class="badge bg-${entry.action_class}">${entry.action}</span></p>
                </div>
                
                <div class="mb-3">
                    <h6>Resource</h6>
                    <p>${entry.resource}</p>
                </div>
                
                <div class="mb-3">
                    <h6>IP Address</h6>
                    <p>${entry.ip_address}</p>
                </div>
                
                <div class="mb-3">
                    <h6>User Agent</h6>
                    <p>${entry.user_agent}</p>
                </div>
                
                <div class="mb-3">
                    <h6>Changes</h6>
                    <pre class="bg-light p-3"><code>${JSON.stringify(entry.changes || {}, null, 2)}</code></pre>
                </div>
                
                <div class="mb-3">
                    <h6>Additional Data</h6>
                    <pre class="bg-light p-3"><code>${JSON.stringify(entry.additional_data || {}, null, 2)}</code></pre>
                </div>
            `;
            
            $('#auditDetailsModal').modal('show');
        })
        .catch(error => {
            console.error('Error loading audit details:', error);
            showNotification('Error loading audit details', 'error');
        });
}

function exportAudit(format) {
    const filters = {
        action_type: $('[name=action_type]').val(),
        user_id: $('[name=user_id]').val(),
        date_range: $('[name=date_range]').val(),
        format: format
    };
    
    window.location.href = '/admin/audit/export?' + new URLSearchParams(filters);
} 