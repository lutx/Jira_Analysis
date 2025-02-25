document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

function saveJiraConfig() {
    const form = $('#jiraConfigForm');
    const data = {
        url: form.find('[name=url]').val(),
        username: form.find('[name=username]').val(),
        api_token: form.find('[name=api_token]').val(),
        project_key: form.find('[name=project_key]').val()
    };
    
    fetch('/admin/settings/jira', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            showNotification(result.message, 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving JIRA config:', error);
        showNotification('Error saving JIRA configuration', 'error');
    });
}

function testJiraConnection() {
    fetch('/admin/settings/jira/test', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            showNotification(result.message, 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error testing JIRA connection:', error);
        showNotification('Error testing JIRA connection', 'error');
    });
}

function saveSystemSettings() {
    const form = $('#systemSettingsForm');
    const data = {
        site_name: form.find('[name=site_name]').val(),
        items_per_page: form.find('[name=items_per_page]').val(),
        enable_notifications: form.find('[name=enable_notifications]').is(':checked')
    };
    
    fetch('/admin/settings/system', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            showNotification(result.message, 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving system settings:', error);
        showNotification('Error saving system settings', 'error');
    });
}

function saveEmailSettings() {
    const form = $('#emailSettingsForm');
    const data = {
        smtp_server: form.find('[name=smtp_server]').val(),
        smtp_port: form.find('[name=smtp_port]').val(),
        smtp_username: form.find('[name=smtp_username]').val(),
        smtp_password: form.find('[name=smtp_password]').val()
    };
    
    fetch('/admin/settings/email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            showNotification(result.message, 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving email settings:', error);
        showNotification('Error saving email settings', 'error');
    });
}

function testEmailSettings() {
    fetch('/admin/settings/email/test', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            showNotification(result.message, 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error testing email settings:', error);
        showNotification('Error testing email settings', 'error');
    });
} 