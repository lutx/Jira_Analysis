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