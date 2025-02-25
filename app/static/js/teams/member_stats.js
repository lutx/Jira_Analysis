let hoursChart = null;
let tasksChart = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeDatePickers();
    initializeCharts();
    loadStats();
});

function initializeDatePickers() {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    document.getElementById('startDate').valueAsDate = thirtyDaysAgo;
    document.getElementById('endDate').valueAsDate = today;
}

function initializeCharts() {
    // Wykres godzin
    const hoursCtx = document.getElementById('hoursChart').getContext('2d');
    hoursChart = new Chart(hoursCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Godziny',
                data: [],
                borderColor: '#007bff',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Dzienna liczba godzin'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Wykres zadań
    const tasksCtx = document.getElementById('tasksChart').getContext('2d');
    tasksChart = new Chart(tasksCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Zadania',
                data: [],
                borderColor: '#28a745',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Dzienna liczba zadań'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

async function loadStats() {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        const response = await fetch(`/api/teams/${teamId}/members/${userName}/stats?start_date=${startDate}&end_date=${endDate}`);
        const stats = await response.json();
        
        if (!response.ok) {
            throw new Error(stats.error || 'Błąd podczas ładowania statystyk');
        }
        
        updateSummary(stats);
        updateCharts(stats);
        updateProjectsList(stats);
        updateTable(stats);
        
    } catch (error) {
        console.error('Error loading stats:', error);
        showError('Błąd podczas ładowania statystyk');
    }
}

function updateSummary(stats) {
    document.getElementById('totalHours').textContent = stats.total_hours.toFixed(1);
    document.getElementById('totalTasks').textContent = stats.total_tasks;
    document.getElementById('avgDailyHours').textContent = stats.avg_daily_hours.toFixed(1);
    document.getElementById('avgTasksPerDay').textContent = stats.avg_tasks_per_day.toFixed(1);
}

function updateCharts(stats) {
    const dates = Object.keys(stats.daily_stats).sort();
    const hours = dates.map(date => stats.daily_stats[date].hours);
    const tasks = dates.map(date => stats.daily_stats[date].tasks);
    
    hoursChart.data.labels = dates;
    hoursChart.data.datasets[0].data = hours;
    hoursChart.update();
    
    tasksChart.data.labels = dates;
    tasksChart.data.datasets[0].data = tasks;
    tasksChart.update();
}

function updateProjectsList(stats) {
    const projectsList = document.getElementById('projectsList');
    projectsList.innerHTML = '';
    
    stats.projects.forEach(project => {
        const item = document.createElement('a');
        item.href = `#`;
        item.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        item.textContent = project;
        projectsList.appendChild(item);
    });
}

function updateTable(stats) {
    const tbody = document.getElementById('statsTable').getElementsByTagName('tbody')[0];
    tbody.innerHTML = '';
    
    Object.entries(stats.daily_stats)
        .sort(([a], [b]) => a.localeCompare(b))
        .forEach(([date, data]) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${date}</td>
                <td>${data.hours.toFixed(1)}</td>
                <td>${data.tasks}</td>
                <td>${data.projects.join(', ')}</td>
            `;
            tbody.appendChild(tr);
        });
}

async function exportStats(format) {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        const url = `/api/teams/${teamId}/members/${userName}/stats/export?start_date=${startDate}&end_date=${endDate}&format=${format}`;
        window.location.href = url;
        
    } catch (error) {
        console.error('Error exporting stats:', error);
        showError('Błąd podczas eksportu statystyk');
    }
}

function showError(message) {
    // Implementacja wyświetlania błędu
    alert(message);
} 