document.addEventListener('DOMContentLoaded', function() {
    // Handle form submissions
    $('#generalSettingsForm').on('submit', function(e) {
        e.preventDefault();
        saveSettings('general');
    });
    
    $('#emailSettingsForm').on('submit', function(e) {
        e.preventDefault();
        saveSettings('email');
    });
    
    $('#securitySettingsForm').on('submit', function(e) {
        e.preventDefault();
        saveSettings('security');
    });
    
    $('#backupSettingsForm').on('submit', function(e) {
        e.preventDefault();
        saveSettings('backup');
    });
});

function saveSettings(section) {
    const form = $(`#${section}SettingsForm`);
    const formData = new FormData(form[0]);
    const settings = {};
    
    for (const [key, value] of formData.entries()) {
        settings[key] = value;
    }
    
    fetch(`/admin/settings/${section}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            showNotification(`${section.charAt(0).toUpperCase() + section.slice(1)} settings saved successfully`, 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error(`Error saving ${section} settings:`, error);
        showNotification(`Error saving ${section} settings`, 'error');
    });
}

function testEmailSettings() {
    $('#testEmailModal').modal('show');
}

function sendTestEmail() {
    const testEmail = $('[name=test_email]').val();
    
    fetch('/admin/settings/email/test', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({ email: testEmail })
    })
    .then(response => response.json())
    .then(result => {
        $('#testEmailModal').modal('hide');
        if (result.status === 'success') {
            showNotification('Test email sent successfully', 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error sending test email:', error);
        showNotification('Error sending test email', 'error');
        $('#testEmailModal').modal('hide');
    });
}

function createBackup() {
    const button = document.querySelector('button[onclick="createBackup()"]');
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="bi bi-arrow-repeat"></i> Creating Backup...';
    
    fetch('/admin/settings/backup/create', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            showNotification('Backup created successfully', 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error creating backup:', error);
        showNotification('Error creating backup', 'error');
    })
    .finally(() => {
        button.disabled = false;
        button.innerHTML = originalText;
    });
} 