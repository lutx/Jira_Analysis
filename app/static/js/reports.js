// Inicjalizacja komponentów dla raportów
document.addEventListener('DOMContentLoaded', function() {
    // Obsługa filtrów
    const filterForm = document.getElementById('reportFilters');
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            updateReport();
        });
    }

    // Obsługa exportu
    const exportBtn = document.getElementById('exportReport');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportReport);
    }

    // Inicjalizacja datepickerów
    initializeDatePickers();
});

// Funkcja aktualizacji raportu
async function updateReport() {
    try {
        const filters = new FormData(document.getElementById('reportFilters'));
        const response = await fetch('/api/reports/data?' + new URLSearchParams(filters), {
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        });
        
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        updateReportView(data);
    } catch (error) {
        console.error('Error updating report:', error);
        showToast('error', 'Błąd podczas aktualizacji raportu');
    }
}

// Funkcja exportu raportu
async function exportReport() {
    try {
        const filters = new FormData(document.getElementById('reportFilters'));
        const response = await fetch('/api/reports/export?' + new URLSearchParams(filters), {
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        });
        
        if (!response.ok) throw new Error('Network response was not ok');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'report.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Error exporting report:', error);
        showToast('error', 'Błąd podczas eksportu raportu');
    }
}

// Inicjalizacja datepickerów
function initializeDatePickers() {
    const dateInputs = document.querySelectorAll('.datepicker');
    dateInputs.forEach(input => {
        new bootstrap.Datepicker(input, {
            format: 'yyyy-mm-dd',
            autoclose: true
        });
    });
}

// Inicjalizacja filtrów
function initializeFilters() {
    // Pobierz projekty
    fetch('/api/projects', {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    })
    .then(response => response.json())
    .then(data => {
        const select = document.getElementById('projectFilter');
        data.forEach(project => {
            const option = document.createElement('option');
            option.value = project.key;
            option.textContent = project.name;
            select.appendChild(option);
        });
    })
    .catch(error => console.error('Error loading projects:', error));
}

// Ładowanie danych raportu
async function loadReportData() {
    try {
        showLoading();
        
        const filters = getFilters();
        const response = await fetch('/api/reports/data', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filters)
        });

        if (!response.ok) {
            throw new Error('Błąd podczas pobierania danych');
        }

        const data = await response.json();
        updateReport(data);
        updateCharts(data);
        updateSummary(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError('Błąd podczas ładowania danych raportu');
    } finally {
        hideLoading();
    }
}

// Pobranie wartości filtrów
function getFilters() {
    return {
        startDate: document.getElementById('startDate').value,
        endDate: document.getElementById('endDate').value,
        project: document.getElementById('projectFilter').value,
        user: document.getElementById('userFilter').value,
        groupBy: document.getElementById('groupByFilter').value
    };
}

// Aktualizacja tabeli raportu
function updateReport(data) {
    const tbody = document.querySelector('#reportTable tbody');
    tbody.innerHTML = '';

    if (data.items && data.items.length > 0) {
        data.items.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${formatDate(item.date)}</td>
                <td>${item.project}</td>
                <td>${item.issue}</td>
                <td>${item.user}</td>
                <td>${formatTime(item.timeSpent)}</td>
                <td>${item.description || ''}</td>
            `;
            tbody.appendChild(row);
        });
    } else {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="6" class="text-center">Brak danych</td>';
        tbody.appendChild(row);
    }
}

// Aktualizacja wykresów
function updateCharts(data) {
    // Wykres czasu według projektu
    const projectChartCtx = document.getElementById('projectChart').getContext('2d');
    new Chart(projectChartCtx, {
        type: 'pie',
        data: {
            labels: data.projectStats.map(item => item.name),
            datasets: [{
                data: data.projectStats.map(item => item.timeSpent),
                backgroundColor: generateColors(data.projectStats.length)
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    // Wykres trendu czasowego
    const trendChartCtx = document.getElementById('trendChart').getContext('2d');
    new Chart(trendChartCtx, {
        type: 'line',
        data: {
            labels: data.trend.map(item => item.date),
            datasets: [{
                label: 'Czas pracy',
                data: data.trend.map(item => item.timeSpent),
                borderColor: 'rgba(0, 82, 204, 1)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Aktualizacja podsumowania
function updateSummary(data) {
    document.getElementById('totalTime').textContent = formatTime(data.summary.totalTime);
    document.getElementById('avgDailyTime').textContent = formatTime(data.summary.avgDailyTime);
    document.getElementById('totalIssues').textContent = data.summary.totalIssues;
    document.getElementById('totalProjects').textContent = data.summary.totalProjects;
}

// Eksport do Excela
function exportToExcel() {
    const filters = getFilters();
    window.location.href = `/api/reports/export/excel?${new URLSearchParams(filters)}`;
}

// Eksport do PDF
function exportToPDF() {
    const filters = getFilters();
    window.location.href = `/api/reports/export/pdf?${new URLSearchParams(filters)}`;
}

// Funkcje pomocnicze
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pl-PL');
}

function formatTime(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
}

function generateColors(count) {
    const colors = [];
    for (let i = 0; i < count; i++) {
        const hue = (i * 137.508) % 360; // Złoty kąt
        colors.push(`hsla(${hue}, 70%, 60%, 0.7)`);
    }
    return colors;
}

function showLoading() {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="spinner-border" role="status">
            <span class="visually-hidden">Ładowanie...</span>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

function showError(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('.reports-container').prepend(alertDiv);
} 