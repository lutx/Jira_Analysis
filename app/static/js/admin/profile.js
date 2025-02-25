document.addEventListener('DOMContentLoaded', function() {
    // Handle profile form submission
    $('#profileForm').on('submit', function(e) {
        e.preventDefault();
        saveProfile();
    });
    
    // Handle password form submission
    $('#passwordForm').on('submit', function(e) {
        e.preventDefault();
        changePassword();
    });
});

function saveProfile() {
    const formData = new FormData($('#profileForm')[0]);
    const data = {
        username: formData.get('username'),
        email: formData.get('email'),
        display_name: formData.get('display_name')
    };
    
    fetch('/admin/profile', {
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
            showNotification('Profile updated successfully', 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving profile:', error);
        showNotification('Error saving profile', 'error');
    });
}

function changePassword() {
    const formData = new FormData($('#passwordForm')[0]);
    const data = {
        current_password: formData.get('current_password'),
        new_password: formData.get('new_password'),
        confirm_password: formData.get('confirm_password')
    };
    
    fetch('/admin/profile/password', {
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
            showNotification('Password changed successfully', 'success');
            $('#passwordForm')[0].reset();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error changing password:', error);
        showNotification('Error changing password', 'error');
    });
}

function setup2FA() {
    fetch('/admin/profile/2fa/setup')
        .then(response => response.json())
        .then(data => {
            document.getElementById('qrCode').src = data.qr_code;
            document.getElementById('secretKey').textContent = data.secret;
            $('#setup2FAModal').modal('show');
        })
        .catch(error => {
            console.error('Error setting up 2FA:', error);
            showNotification('Error setting up 2FA', 'error');
        });
}

function verify2FA() {
    const code = document.querySelector('#verify2FAForm [name=code]').value;
    
    fetch('/admin/profile/2fa/verify', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({ code })
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            $('#setup2FAModal').modal('hide');
            showRecoveryCodes(result.recovery_codes);
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error verifying 2FA:', error);
        showNotification('Error verifying 2FA', 'error');
    });
}

function disable2FA() {
    if (confirm('Are you sure you want to disable two-factor authentication?')) {
        fetch('/admin/profile/2fa/disable', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                showNotification('2FA disabled successfully', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(result.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error disabling 2FA:', error);
            showNotification('Error disabling 2FA', 'error');
        });
    }
}

function showRecoveryCodes(codes) {
    fetch('/admin/profile/2fa/recovery-codes')
        .then(response => response.json())
        .then(data => {
            document.getElementById('recoveryCodes').textContent = 
                (codes || data.codes).join('\n');
            $('#recoveryCodesModal').modal('show');
        })
        .catch(error => {
            console.error('Error loading recovery codes:', error);
            showNotification('Error loading recovery codes', 'error');
        });
}

function copyRecoveryCodes() {
    const codes = document.getElementById('recoveryCodes').textContent;
    navigator.clipboard.writeText(codes)
        .then(() => {
            showNotification('Recovery codes copied to clipboard', 'success');
        })
        .catch(error => {
            console.error('Error copying recovery codes:', error);
            showNotification('Error copying recovery codes', 'error');
        });
}

function generateApiKey() {
    $('#apiKeyModal').modal('show');
}

function createApiKey() {
    const keyName = document.querySelector('#apiKeyForm [name=key_name]').value;
    
    fetch('/admin/profile/api-keys', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({ name: keyName })
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            $('#apiKeyModal').modal('hide');
            Swal.fire({
                title: 'API Key Generated',
                html: `
                    <p>Your API key has been generated. Please copy it now as it won't be shown again:</p>
                    <pre class="bg-light p-3">${result.api_key}</pre>
                `,
                icon: 'success',
                confirmButtonText: 'Copy & Close',
            }).then((result) => {
                if (result.isConfirmed) {
                    navigator.clipboard.writeText(result.api_key);
                    location.reload();
                }
            });
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error generating API key:', error);
        showNotification('Error generating API key', 'error');
    });
}

function revokeApiKey(keyId) {
    if (confirm('Are you sure you want to revoke this API key?')) {
        fetch(`/admin/profile/api-keys/${keyId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                showNotification('API key revoked successfully', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(result.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error revoking API key:', error);
            showNotification('Error revoking API key', 'error');
        });
    }
} 