let dailyActivityChart = null;
let userActivityChart = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeDatePickers();
    initializeCharts();
    loadReport();
});

function initializeDatePickers() {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    document.getElementById('startDate').valueAsDate = thirtyDaysAgo;
    document.getElementById('endDate').valueAsDate = today;
}

function initializeCharts() {
    // Wykres aktywności dziennej
    const dailyCtx = document.getElementById('dailyActivityChart').getContext('2d');
    dailyActivityChart = new Chart(dailyCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Godziny dziennie',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Aktywność dzienna'
                }
            }
        }
    });

    // Wykres aktywności użytkowników
    const userCtx = document.getElementById('userActivityChart').getContext('2d');
    userActivityChart = new Chart(userCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Łączne godziny',
                data: [],
                backgroundColor: 'rgb(54, 162, 235)'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Aktywność użytkowników'
                }
            }
        }
    });
}

async function loadReport() {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        const response = await fetch(`/api/reports/activity?start_date=${startDate}&end_date=${endDate}`);
        const report = await response.json();
        
        if (!response.ok) {
            throw new Error(report.error || 'Błąd podczas generowania raportu');
        }
        
        updateSummary(report);
        updateCharts(report);
        updateTable(report);
        
    } catch (error) {
        console.error('Error loading report:', error);
        showError(error.message);
    }
}

function updateSummary(report) {
    document.getElementById('totalHours').textContent = report.total_hours.toFixed(1);
    document.getElementById('totalTasks').textContent = report.total_tasks;
    document.getElementById('activeUsers').textContent = Object.keys(report.user_summary).length;
    
    const days = Object.keys(report.daily_activity).length;
    const avgHours = days > 0 ? report.total_hours / days : 0;
    document.getElementById('avgHoursPerDay').textContent = avgHours.toFixed(1);
}

function updateCharts(report) {
    // Aktualizacja wykresu dziennego
    const dates = Object.keys(report.daily_activity).sort();
    const dailyHours = dates.map(date => report.daily_activity[date].total_hours);
    
    dailyActivityChart.data.labels = dates;
    dailyActivityChart.data.datasets[0].data = dailyHours;
    dailyActivityChart.update();
    
    // Aktualizacja wykresu użytkowników
    const users = Object.keys(report.user_summary);
    const userHours = users.map(user => report.user_summary[user].total_hours);
    
    userActivityChart.data.labels = users;
    userActivityChart.data.datasets[0].data = userHours;
    userActivityChart.update();
}

function updateTable(report) {
    const tbody = document.querySelector('#activityTable tbody');
    tbody.innerHTML = '';
    
    for (const date in report.daily_activity) {
        for (const user in report.daily_activity[date].users) {
            const data = report.daily_activity[date].users[user];
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${date}</td>
                <td>${user}</td>
                <td>${data.hours.toFixed(1)}</td>
                <td>${data.tasks}</td>
            `;
            tbody.appendChild(tr);
        }
    }
}

async function exportReport(format) {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        const url = `/api/reports/export/activity?start_date=${startDate}&end_date=${endDate}&format=${format}`;
        window.location.href = url;
        
    } catch (error) {
        console.error('Error exporting report:', error);
        showError('Błąd podczas eksportu raportu');
    }
}

function showError(message) {
    // Implementacja wyświetlania błędu
    alert(message);
} 