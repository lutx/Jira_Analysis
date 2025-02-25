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
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Godziny',
                data: [],
                backgroundColor: '#007bff'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Godziny pracy według użytkowników'
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
        type: 'pie',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#28a745',
                    '#007bff',
                    '#ffc107',
                    '#dc3545',
                    '#6f42c1',
                    '#fd7e14',
                    '#20c997',
                    '#e83e8c'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Udział w projekcie'
                }
            }
        }
    });
}

async function loadStats() {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        const response = await fetch(`/api/teams/${teamId}/projects/${projectKey}/stats?start_date=${startDate}&end_date=${endDate}`);
        const stats = await response.json();
        
        if (!response.ok) {
            throw new Error(stats.error || 'Błąd podczas ładowania statystyk');
        }
        
        updateSummary(stats);
        updateCharts(stats);
        updateTable(stats);
        
    } catch (error) {
        console.error('Error loading stats:', error);
        showError('Błąd podczas ładowania statystyk');
    }
}

function updateSummary(stats) {
    document.getElementById('totalHours').textContent = stats.total_hours.toFixed(1);
    document.getElementById('totalTasks').textContent = stats.total_tasks;
    document.getElementById('avgHoursPerUser').textContent = stats.avg_hours_per_user.toFixed(1);
}

function updateCharts(stats) {
    const users = Object.keys(stats.users);
    const hours = users.map(user => stats.users[user].hours);
    const percentages = users.map(user => (stats.users[user].hours / stats.total_hours * 100));
    
    hoursChart.data.labels = users;
    hoursChart.data.datasets[0].data = hours;
    hoursChart.update();
    
    tasksChart.data.labels = users;
    tasksChart.data.datasets[0].data = percentages;
    tasksChart.update();
}

function updateTable(stats) {
    const tbody = document.getElementById('statsTable').getElementsByTagName('tbody')[0];
    tbody.innerHTML = '';
    
    Object.entries(stats.users)
        .sort(([, a], [, b]) => b.hours - a.hours)
        .forEach(([user, data]) => {
            const percentage = (data.hours / stats.total_hours * 100).toFixed(1);
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${user}</td>
                <td>${data.hours.toFixed(1)}</td>
                <td>${data.tasks}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress flex-grow-1 me-2" style="height: 5px;">
                            <div class="progress-bar" style="width: ${percentage}%"></div>
                        </div>
                        ${percentage}%
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
}

async function exportStats(format) {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        const url = `/api/teams/${teamId}/projects/${projectKey}/stats/export?start_date=${startDate}&end_date=${endDate}&format=${format}`;
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