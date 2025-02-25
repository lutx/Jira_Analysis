document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
    initializeCharts();
    
    // Odświeżanie co 5 minut
    setInterval(loadDashboardData, 5 * 60 * 1000);
    
    // Obsługa przycisku odświeżania
    document.getElementById('refreshData').addEventListener('click', loadDashboardData);
});

async function loadDashboardData() {
    try {
        showLoading();
        
        const response = await fetch('/api/dashboard/stats', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Błąd podczas pobierania danych');
        }

        const data = await response.json();
        updateDashboard(data);
        updateCharts(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError('Błąd podczas ładowania danych');
    } finally {
        hideLoading();
    }
}

function updateDashboard(data) {
    // Aktualizuj statystyki
    document.getElementById('todayWorklogs').textContent = data.today || 0;
    document.getElementById('weeklyWorklogs').textContent = data.weekly || 0;
    document.getElementById('monthlyWorklogs').textContent = data.monthly || 0;

    // Aktualizuj tabelę ostatniej aktywności
    const tbody = document.querySelector('#recentActivity tbody');
    tbody.innerHTML = '';

    if (data.recent && data.recent.length > 0) {
        data.recent.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${formatDate(item.work_date)}</td>
                <td>${item.jira_id}</td>
                <td>${formatTime(item.time_spent)}</td>
                <td>${item.description || ''}</td>
            `;
            tbody.appendChild(row);
        });
    } else {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="4" class="text-center">Brak danych</td>';
        tbody.appendChild(row);
    }
}

function initializeCharts() {
    // Wykres aktywności
    const activityCtx = document.getElementById('activityChart').getContext('2d');
    window.activityChart = new Chart(activityCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Liczba worklogów',
                data: [],
                backgroundColor: 'rgba(0, 82, 204, 0.5)',
                borderColor: 'rgba(0, 82, 204, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });

    // Wykres projektów
    const projectsCtx = document.getElementById('projectsChart').getContext('2d');
    window.projectsChart = new Chart(projectsCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'rgba(0, 82, 204, 0.5)',
                    'rgba(54, 179, 126, 0.5)',
                    'rgba(255, 86, 48, 0.5)',
                    'rgba(255, 171, 0, 0.5)'
                ],
                borderColor: [
                    'rgba(0, 82, 204, 1)',
                    'rgba(54, 179, 126, 1)',
                    'rgba(255, 86, 48, 1)',
                    'rgba(255, 171, 0, 1)'
                ],
                borderWidth: 1
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
}

function updateCharts(data) {
    // Aktualizuj wykres aktywności
    if (window.activityChart && data.activity) {
        window.activityChart.data.labels = data.activity.map(item => item.date);
        window.activityChart.data.datasets[0].data = data.activity.map(item => item.count);
        window.activityChart.update();
    }

    // Aktualizuj wykres projektów
    if (window.projectsChart && data.projects) {
        window.projectsChart.data.labels = data.projects.map(item => item.name);
        window.projectsChart.data.datasets[0].data = data.projects.map(item => item.count);
        window.projectsChart.update();
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pl-PL');
}

function formatTime(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
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
    document.querySelector('.dashboard-container').prepend(alertDiv);
} 