document.addEventListener('DOMContentLoaded', function() {
    const notifications = document.querySelector('.notifications-container');
    
    // Funkcja do tworzenia powiadomienia
    function createNotification(message, type = 'info') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        notifications.appendChild(alert);
        
        // Automatyczne ukrywanie
        setTimeout(() => {
            alert.classList.add('hiding');
            setTimeout(() => alert.remove(), 300);
        }, 5000);
        
        // Obsługa przycisku zamykania
        alert.querySelector('.btn-close').addEventListener('click', () => {
            alert.classList.add('hiding');
            setTimeout(() => alert.remove(), 300);
        });
    }

    // Nasłuchuj na zdarzenia flash messages
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.classList.add('hiding');
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // Eksportuj funkcję do globalnego scope
    window.showNotification = createNotification;

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
    $('#notificationFilters').on('submit', function(e) {
        e.preventDefault();
        updateNotifications();
    });
    
    // Request desktop notification permission
    if ('Notification' in window) {
        Notification.requestPermission();
    }
});

function updateNotifications() {
    const filters = {
        type: $('[name=type]').val(),
        status: $('[name=status]').val(),
        date_range: $('[name=date_range]').val()
    };
    
    fetch('/admin/notifications/data?' + new URLSearchParams(filters))
        .then(response => response.json())
        .then(data => {
            const container = document.querySelector('.list-group');
            container.innerHTML = '';
            
            if (data.notifications.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-4">
                        <i class="bi bi-bell-slash display-4"></i>
                        <p class="mt-2">No notifications found</p>
                    </div>
                `;
                return;
            }
            
            data.notifications.forEach(notification => {
                container.innerHTML += `
                    <div class="list-group-item list-group-item-action ${!notification.is_read ? 'active' : ''}">
                        <div class="d-flex w-100 justify-content-between align-items-center">
                            <h5 class="mb-1">
                                <i class="bi ${notification.icon_class} me-2"></i>
                                ${notification.title}
                            </h5>
                            <small class="text-muted">${moment(notification.created_at).fromNow()}</small>
                        </div>
                        <p class="mb-1">${notification.message}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">
                                Type: <span class="badge bg-${notification.type_class}">${notification.type}</span>
                            </small>
                            <div class="btn-group">
                                ${notification.action_url ? `
                                    <a href="${notification.action_url}" class="btn btn-sm btn-primary">
                                        <i class="bi bi-box-arrow-up-right"></i> View
                                    </a>
                                ` : ''}
                                ${!notification.is_read ? `
                                    <button class="btn btn-sm btn-success" onclick="markAsRead('${notification.id}')">
                                        <i class="bi bi-check"></i> Mark as Read
                                    </button>
                                ` : ''}
                                <button class="btn btn-sm btn-danger" onclick="deleteNotification('${notification.id}')">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });
        })
        .catch(error => {
            console.error('Error updating notifications:', error);
            showNotification('Error updating notifications', 'error');
        });
}

function markAsRead(notificationId) {
    fetch(`/admin/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            updateNotifications();
            updateUnreadCount();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error marking notification as read:', error);
        showNotification('Error marking notification as read', 'error');
    });
}

function markAllAsRead() {
    fetch('/admin/notifications/mark-all-read', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            updateNotifications();
            updateUnreadCount();
            showNotification('All notifications marked as read', 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error marking all notifications as read:', error);
        showNotification('Error marking all notifications as read', 'error');
    });
}

function deleteNotification(notificationId) {
    if (confirm('Are you sure you want to delete this notification?')) {
        fetch(`/admin/notifications/${notificationId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                updateNotifications();
                updateUnreadCount();
            } else {
                showNotification(result.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting notification:', error);
            showNotification('Error deleting notification', 'error');
        });
    }
}

function clearAll() {
    if (confirm('Are you sure you want to delete all notifications?')) {
        fetch('/admin/notifications/clear', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                updateNotifications();
                updateUnreadCount();
                showNotification('All notifications cleared', 'success');
            } else {
                showNotification(result.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error clearing notifications:', error);
            showNotification('Error clearing notifications', 'error');
        });
    }
}

function updateUnreadCount() {
    fetch('/admin/notifications/unread-count')
        .then(response => response.json())
        .then(data => {
            const badge = document.querySelector('#notificationBadge');
            if (badge) {
                badge.textContent = data.count;
                badge.style.display = data.count > 0 ? 'inline' : 'none';
            }
        })
        .catch(error => {
            console.error('Error updating unread count:', error);
        });
}

function showNotificationSettings() {
    fetch('/admin/notifications/settings')
        .then(response => response.json())
        .then(settings => {
            // Set form values
            $('#emailEnabled').prop('checked', settings.email_enabled);
            $('#desktopEnabled').prop('checked', settings.desktop_enabled);
            $('#systemNotifications').prop('checked', settings.system_notifications);
            $('#alertNotifications').prop('checked', settings.alert_notifications);
            $('#taskNotifications').prop('checked', settings.task_notifications);
            $('#messageNotifications').prop('checked', settings.message_notifications);
            
            $('#notificationSettingsModal').modal('show');
        })
        .catch(error => {
            console.error('Error loading notification settings:', error);
            showNotification('Error loading notification settings', 'error');
        });
}

function saveNotificationSettings() {
    const settings = {
        email_enabled: $('#emailEnabled').is(':checked'),
        desktop_enabled: $('#desktopEnabled').is(':checked'),
        system_notifications: $('#systemNotifications').is(':checked'),
        alert_notifications: $('#alertNotifications').is(':checked'),
        task_notifications: $('#taskNotifications').is(':checked'),
        message_notifications: $('#messageNotifications').is(':checked')
    };
    
    fetch('/admin/notifications/settings', {
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
            $('#notificationSettingsModal').modal('hide');
            showNotification('Notification settings saved', 'success');
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving notification settings:', error);
        showNotification('Error saving notification settings', 'error');
    });
} 