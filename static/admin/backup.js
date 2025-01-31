document.addEventListener('DOMContentLoaded', function() {
    loadBackups();
    
    document.getElementById('restoreForm').addEventListener('submit', function(e) {
        e.preventDefault();
        showConfirmDialog(
            'Czy na pewno chcesz przywrócić bazę danych z backupu? Ta operacja nadpisze wszystkie obecne dane.',
            restoreBackup
        );
    });
});

async function loadBackups() {
    try {
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
    }
}

function displayBackups(backups) {
    const tbody = document.querySelector('#backupsTable tbody');
    tbody.innerHTML = '';
    
    backups.forEach(backup => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(backup.created_at)}</td>
            <td>${formatSize(backup.size)}</td>
            <td>${backup.created_by}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="downloadBackup('${backup.id}')">
                    <i class="bi bi-download"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteBackup('${backup.id}')">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function updateLastBackupInfo(lastBackup) {
    const info = document.getElementById('lastBackupInfo');
    if (lastBackup) {
        info.textContent = `${formatDate(lastBackup.created_at)} (${formatSize(lastBackup.size)})`;
    } else {
        info.textContent = 'Brak backupów';
    }
}

async function createBackup() {
    try {
        const response = await fetch('/api/admin/backups', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Błąd podczas tworzenia backupu');
        }
        
        showSuccess('Backup został utworzony');
        loadBackups();
        
    } catch (error) {
        console.error('Error creating backup:', error);
        showError('Błąd podczas tworzenia backupu');
    }
}

async function downloadBackup(backupId) {
    try {
        const response = await fetch(`/api/admin/backups/${backupId}/download`);
        const blob = await response.blob();
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `backup_${backupId}.sql.gz`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        
    } catch (error) {
        console.error('Error downloading backup:', error);
        showError('Błąd podczas pobierania backupu');
    }
}

async function deleteBackup(backupId) {
    showConfirmDialog(
        'Czy na pewno chcesz usunąć ten backup?',
        async () => {
            try {
                const response = await fetch(`/api/admin/backups/${backupId}`, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Błąd podczas usuwania backupu');
                }
                
                showSuccess('Backup został usunięty');
                loadBackups();
                
            } catch (error) {
                console.error('Error deleting backup:', error);
                showError('Błąd podczas usuwania backupu');
            }
        }
    );
}

async function restoreBackup() {
    try {
        const fileInput = document.getElementById('backupFile');
        if (!fileInput.files.length) {
            showError('Wybierz plik backupu');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        
        const response = await fetch('/api/admin/backups/restore', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Błąd podczas przywracania backupu');
        }
        
        showSuccess('Baza danych została przywrócona z backupu');
        window.location.reload();
        
    } catch (error) {
        console.error('Error restoring backup:', error);
        showError('Błąd podczas przywracania backupu');
    }
}

function showConfirmDialog(message, onConfirm) {
    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    document.getElementById('confirmMessage').textContent = message;
    
    const confirmButton = document.getElementById('confirmButton');
    const oldClickHandler = confirmButton.onclick;
    confirmButton.onclick = () => {
        modal.hide();
        onConfirm();
        confirmButton.onclick = oldClickHandler;
    };
    
    modal.show();
}

function formatDate(timestamp) {
    return new Date(timestamp).toLocaleString('pl-PL');
}

function formatSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`;
}

function showSuccess(message) {
    alert(message); // Tymczasowo używamy alert
}

function showError(message) {
    alert(message); // Tymczasowo używamy alert
} 