let workloadChart = null;
let activityChart = null;

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
    // Wykres obciążenia
    const workloadCtx = document.getElementById('workloadChart').getContext('2d');
    workloadChart = new Chart(workloadCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Obciążenie (%)',
                data: [],
                backgroundColor: [],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 150
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Obciążenie członków zespołu'
                }
            }
        }
    });

    // Wykres aktywności
    const activityCtx = document.getElementById('activityChart').getContext('2d');
    activityChart = new Chart(activityCtx, {
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
                    text: 'Aktywność dzienna zespołu'
                }
            }
        }
    });
}

async function loadReport() {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const reportType = document.getElementById('reportType').value;
        
        const response = await fetch(`/api/teams/reports/${reportType}?start_date=${startDate}&end_date=${endDate}`);
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
    document.getElementById('avgWorkload').textContent = `${report.avg_workload.toFixed(1)}%`;
    document.getElementById('activeMembers').textContent = Object.keys(report.users).length;
}

function updateCharts(report) {
    // Aktualizacja wykresu obciążenia
    const users = Object.keys(report.users);
    const workloads = users.map(user => report.users[user].workload);
    const colors = workloads.map(workload => getWorkloadColor(workload));
    
    workloadChart.data.labels = users;
    workloadChart.data.datasets[0].data = workloads;
    workloadChart.data.datasets[0].backgroundColor = colors;
    workloadChart.update();
    
    // Aktualizacja wykresu aktywności
    const dates = Object.keys(report.daily_activity).sort();
    const hours = dates.map(date => report.daily_activity[date]);
    
    activityChart.data.labels = dates;
    activityChart.data.datasets[0].data = hours;
    activityChart.update();
}

function updateTable(report) {
    const tbody = document.querySelector('#reportTable tbody');
    tbody.innerHTML = '';
    
    for (const user in report.users) {
        const data = report.users[user];
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${user}</td>
            <td>${data.hours.toFixed(1)}</td>
            <td>
                <div class="d-flex align-items-center">
                    <div class="progress flex-grow-1 me-2" style="height: 5px;">
                        <div class="progress-bar" style="width: ${data.workload}%; 
                             background-color: ${getWorkloadColor(data.workload)}">
                        </div>
                    </div>
                    ${data.workload.toFixed(1)}%
                </div>
            </td>
            <td>${data.tasks}</td>
            <td>${data.efficiency.toFixed(1)}%</td>
        `;
        tbody.appendChild(tr);
    }
}

function getWorkloadColor(workload) {
    if (workload > 100) return '#dc3545'; // czerwony
    if (workload >= 80) return '#28a745'; // zielony
    return '#ffc107'; // żółty
}

async function exportReport(format) {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const reportType = document.getElementById('reportType').value;
        
        const url = `/api/teams/reports/export/${reportType}?start_date=${startDate}&end_date=${endDate}&format=${format}`;
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