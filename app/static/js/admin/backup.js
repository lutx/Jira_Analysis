function displayBackups(backups) {
    const tbody = document.querySelector('#backupsTable tbody');
    tbody.innerHTML = '';
    
    backups.forEach(backup => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(backup.created_at)}</td>
            <td>${formatSize(backup.size)}</td>
            <td>${backup.created_by}</td>
            <td class="text-end">
                <button class="btn btn-sm btn-outline-primary btn-action" onclick="downloadBackup('${backup.id}')" title="Pobierz backup">
                    <i class="bi bi-download"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger btn-action" onclick="deleteBackup('${backup.id}')" title="Usuń backup">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function showLoader() {
    document.getElementById('loader').style.display = 'flex';
}

function hideLoader() {
    document.getElementById('loader').style.display = 'none';
}

async function loadBackups() {
    try {
        showLoader();
        const response = await fetch('/api/admin/backups');
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Błąd podczas ładowania backupów');
        }
        
        displayBackups(data.backups);
        updateLastBackupInfo(data.last_backup);
        
    } catch (error) {
        console.error('Error loading backups:', error);
        showError('Błąd podczas ładowania listy backupów');
    } finally {
        hideLoader();
    }
}

// Backup & Restore Management
const BackupManager = {
    init() {
        this.bindEvents();
        this.initializeUI();
    },

    bindEvents() {
        // Backup form submission
        $('#backupForm').on('submit', this.handleBackup.bind(this));
        
        // Restore form submission
        $('#restoreForm').on('submit', this.handleRestore.bind(this));
        
        // Maintenance actions
        $('#optimizeDb').on('click', this.optimizeDatabase.bind(this));
        $('#clearCache').on('click', this.clearCache.bind(this));
    },

    initializeUI() {
        // Initialize file input
        $('input[type="file"]').on('change', function() {
            const fileName = $(this).val().split('\\').pop();
            $(this).next('.custom-file-label').html(fileName);
        });
    },

    async handleBackup(e) {
        e.preventDefault();
        try {
            const form = $(e.target);
            const response = await $.post(form.attr('action'), form.serialize());
            
            if (response.success) {
                toastr.success('Backup created successfully');
                window.location.reload();
            } else {
                toastr.error(response.message || 'Error creating backup');
            }
        } catch (error) {
            console.error('Backup error:', error);
            toastr.error('Error creating backup');
        }
    },

    confirmRestore() {
        return new Promise((resolve) => {
            $('#confirmationMessage').text('Are you sure you want to restore this backup? This will overwrite existing data.');
            $('#confirmActionBtn').off('click').on('click', () => {
                $('#confirmationModal').modal('hide');
                resolve(true);
            });
            $('#confirmationModal').modal('show');
        });
    },

    async handleRestore(e) {
        e.preventDefault();
        
        if (!await this.confirmRestore()) {
            return;
        }

        const formData = new FormData(e.target);
        
        try {
            const response = await $.ajax({
                url: $(e.target).attr('action'),
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false
            });
            
            if (response.success) {
                toastr.success('Backup restored successfully');
                window.location.reload();
            } else {
                toastr.error(response.message || 'Error restoring backup');
            }
        } catch (error) {
            console.error('Restore error:', error);
            toastr.error('Error restoring backup');
        }
    },

    async deleteBackup(backupId) {
        if (!await this.confirmDelete()) {
            return;
        }

        try {
            const response = await $.ajax({
                url: `/admin/backup/${backupId}`,
                type: 'DELETE'
            });
            
            if (response.success) {
                toastr.success('Backup deleted successfully');
                window.location.reload();
            } else {
                toastr.error(response.message || 'Error deleting backup');
            }
        } catch (error) {
            console.error('Delete error:', error);
            toastr.error('Error deleting backup');
        }
    },

    confirmDelete() {
        return new Promise((resolve) => {
            $('#confirmationMessage').text('Are you sure you want to delete this backup?');
            $('#confirmActionBtn').off('click').on('click', () => {
                $('#confirmationModal').modal('hide');
                resolve(true);
            });
            $('#confirmationModal').modal('show');
        });
    },

    async optimizeDatabase() {
        try {
            const response = await $.post('/admin/backup/optimize');
            if (response.success) {
                toastr.success('Database optimized successfully');
            } else {
                toastr.error(response.message || 'Error optimizing database');
            }
        } catch (error) {
            console.error('Optimize error:', error);
            toastr.error('Error optimizing database');
        }
    },

    async clearCache() {
        try {
            const response = await $.post('/admin/cache/clear');
            if (response.success) {
                toastr.success('Cache cleared successfully');
            } else {
                toastr.error(response.message || 'Error clearing cache');
            }
        } catch (error) {
            console.error('Cache clear error:', error);
            toastr.error('Error clearing cache');
        }
    }
};

// Initialize on document ready
$(document).ready(() => {
    BackupManager.init();
}); 