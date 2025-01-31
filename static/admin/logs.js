document.addEventListener('DOMContentLoaded', function() {
    // Usuń hash z URL
    if (window.location.hash) {
        history.replaceState(null, '', window.location.pathname);
    }
    
    // Ustaw dzisiejszą datę w filtrze
    document.getElementById('logDate').valueAsDate = new Date();
    
    // Załaduj logi
    loadLogs();
    
    // Dodaj nasłuchiwanie na zmiany filtrów
    document.getElementById('logLevel').addEventListener('change', filterLogs);
    document.getElementById('logDate').addEventListener('change', filterLogs);
    document.getElementById('searchText').addEventListener('input', debounce(filterLogs, 500));
});

let currentPage = 1;
const logsPerPage = 50;

function handleNavigation(event) {
    if (event && event.preventDefault) {
        event.preventDefault();
    }
    
    // Reszta kodu obsługi nawigacji...
}

async function loadLogs(page = 1) {
    currentPage = page;
    try {
        const level = document.getElementById('logLevel').value;
        const date = document.getElementById('logDate').value;
        const search = document.getElementById('searchText').value;
        
        const response = await fetch(`/api/admin/logs?page=${page}&level=${level}&date=${date}&search=${search}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Błąd podczas ładowania logów');
        }
        
        displayLogs(data.logs);
        updatePagination(data.total_pages, page);
        
    } catch (error) {
        console.error('Error loading logs:', error);
        showError('Błąd podczas ładowania logów');
    }
}

function displayLogs(logs) {
    const tbody = document.querySelector('#logsTable tbody');
    tbody.innerHTML = '';
    
    logs.forEach(log => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(log.timestamp)}</td>
            <td><span class="badge bg-${getLevelBadgeClass(log.level)}">${log.level}</span></td>
            <td>${log.module}</td>
            <td>
                <div class="text-truncate" style="max-width: 500px;">
                    ${log.message}
                </div>
                <button type="button" class="btn btn-link btn-sm" onclick='showLogDetails(${JSON.stringify(log).replace(/'/g, "&#39;")})'>
                    Szczegóły
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function updatePagination(totalPages, currentPage) {
    const pagination = document.getElementById('logsPagination');
    pagination.innerHTML = '';
    
    // Poprzednia strona
    pagination.innerHTML += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" onclick="handleNavigation(event); loadLogs(${currentPage - 1})" href="javascript:void(0)">
                <i class="bi bi-chevron-left"></i>
            </a>
        </li>
    `;
    
    // Numery stron
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            pagination.innerHTML += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="loadLogs(${i})">${i}</a>
                </li>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            pagination.innerHTML += `
                <li class="page-item disabled">
                    <span class="page-link">...</span>
                </li>
            `;
        }
    }
    
    // Następna strona
    pagination.innerHTML += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadLogs(${currentPage + 1})">
                <i class="bi bi-chevron-right"></i>
            </a>
        </li>
    `;
}

function showLogDetails(log) {
    try {
        const modalElement = document.getElementById('logDetailsModal');
        const modal = new bootstrap.Modal(modalElement);
        
        const formattedDetails = {
            Timestamp: formatDate(log.timestamp),
            Level: log.level,
            Module: log.module,
            Message: log.message
        };
        
        const prettyJson = JSON.stringify(formattedDetails, null, 2)
            .replace(/\\n/g, '\n')
            .replace(/\\"/g, '"');
            
        document.getElementById('logDetails').textContent = prettyJson;
        modal.show();
    } catch (error) {
        console.error('Error showing log details:', error);
        showError('Błąd podczas wyświetlania szczegółów logu');
    }
}

async function downloadLogs() {
    try {
        const level = document.getElementById('logLevel').value;
        const date = document.getElementById('logDate').value;
        const search = document.getElementById('searchText').value;
        
        const response = await fetch(`/api/admin/logs/download?level=${level}&date=${date}&search=${search}`);
        const blob = await response.blob();
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `logs_${date || 'all'}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        
    } catch (error) {
        console.error('Error downloading logs:', error);
        showError('Błąd podczas pobierania logów');
    }
}

function refreshLogs() {
    loadLogs(currentPage);
}

function filterLogs() {
    currentPage = 1;
    loadLogs(1);
}

function getLevelBadgeClass(level) {
    const classes = {
        'ERROR': 'danger',
        'WARNING': 'warning',
        'INFO': 'info',
        'DEBUG': 'secondary'
    };
    return classes[level] || 'secondary';
}

function formatDate(timestamp) {
    try {
        // Usuń nawiasy kwadratowe jeśli istnieją
        timestamp = timestamp.replace(/[\[\]]/g, '');
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) {
            return timestamp; // Jeśli nie można sparsować, zwróć oryginalny string
        }
        return date.toLocaleString('pl-PL', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (e) {
        console.error('Error formatting date:', e);
        return timestamp;
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function showError(message) {
    alert(message); // Tymczasowo używamy alert
} 