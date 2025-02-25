document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const syncHistoryTable = $('#syncHistoryTable').DataTable({
        pageLength: 10,
        order: [[0, 'desc']]
    });
    
    // Handle form submission
    $('#jiraConfigForm').on('submit', function(e) {
        e.preventDefault();
        saveConfiguration();
    });
});

function saveConfiguration() {
    const formData = new FormData($('#jiraConfigForm')[0]);
    const config = {
        url: formData.get('url'),
        username: formData.get('username'),
        api_token: formData.get('api_token'),
        project_key: formData.get('project_key'),
        sync_interval: formData.get('sync_interval'),
        sync_enabled: formData.get('sync_enabled') === 'on'
    };
    
    fetch('/admin/jira/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            showNotification('Configuration saved successfully', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving configuration:', error);
        showNotification('Error saving configuration', 'error');
    });
}

function testConnection() {
    const button = document.querySelector('button[onclick="testConnection()"]');
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="bi bi-arrow-repeat"></i> Testing...';
    
    fetch('/admin/jira/test-connection', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            showNotification('Connection successful', 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error testing connection:', error);
        showNotification('Error testing connection', 'error');
    })
    .finally(() => {
        button.disabled = false;
        button.innerHTML = originalText;
    });
}

function syncData() {
    const button = document.querySelector('button[onclick="syncData()"]');
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="bi bi-arrow-repeat"></i> Syncing...';
    
    fetch('/admin/jira/sync', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            showNotification('Data synced successfully', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error syncing data:', error);
        showNotification('Error syncing data', 'error');
    })
    .finally(() => {
        button.disabled = false;
        button.innerHTML = originalText;
    });
}

function viewSyncDetails(syncId) {
    fetch(`/admin/jira/sync-details/${syncId}`)
        .then(response => response.json())
        .then(details => {
            const content = document.getElementById('syncDetailsContent');
            content.innerHTML = `
                <div class="mb-3">
                    <h6>Summary</h6>
                    <p>Started: ${details.start_time}</p>
                    <p>Completed: ${details.end_time}</p>
                    <p>Duration: ${details.duration}</p>
                    <p>Status: <span class="badge bg-${details.status_class}">${details.status}</span></p>
                </div>
                
                <div class="mb-3">
                    <h6>Items Synced</h6>
                    <ul class="list-group">
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Projects
                            <span class="badge bg-primary rounded-pill">${details.projects_count}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Issues
                            <span class="badge bg-primary rounded-pill">${details.issues_count}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Worklogs
                            <span class="badge bg-primary rounded-pill">${details.worklogs_count}</span>
                        </li>
                    </ul>
                </div>
                
                <div class="mb-3">
                    <h6>Errors</h6>
                    ${details.errors.length > 0 
                        ? `<div class="alert alert-danger">${details.errors.join('<br>')}</div>`
                        : '<p class="text-muted">No errors reported</p>'
                    }
                </div>
            `;
            
            $('#syncDetailsModal').modal('show');
        })
        .catch(error => {
            console.error('Error loading sync details:', error);
            showNotification('Error loading sync details', 'error');
        });
} 