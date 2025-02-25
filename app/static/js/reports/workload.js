let workloadChart = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeDatePickers();
    loadTeams();
    initializeChart();
    loadReport();
});

function initializeDatePickers() {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    document.getElementById('startDate').valueAsDate = thirtyDaysAgo;
    document.getElementById('endDate').valueAsDate = today;
}

async function loadTeams() {
    try {
        const response = await fetch('/api/teams');
        const teams = await response.json();
        
        const teamSelect = document.getElementById('teamSelect');
        teams.forEach(team => {
            teamSelect.add(new Option(team.name, team.id));
        });
        
        teamSelect.addEventListener('change', loadReport);
    } catch (error) {
        console.error('Error loading teams:', error);
        showError('Błąd podczas ładowania zespołów');
    }
}

function initializeChart() {
    const ctx = document.getElementById('workloadChart').getContext('2d');
    workloadChart = new Chart(ctx, {
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
                    max: 150,
                    title: {
                        display: true,
                        text: 'Obciążenie (%)'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Obciążenie użytkowników'
                }
            }
        }
    });
}

async function loadReport() {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const teamId = document.getElementById('teamSelect').value;
        
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate
        });
        if (teamId) params.append('team_id', teamId);
        
        const response = await fetch(`/api/reports/workload?${params}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Błąd podczas generowania raportu');
        }
        
        updateSummary(data);
        updateChart(data);
        updateTable(data);
        
    } catch (error) {
        console.error('Error loading report:', error);
        showError(error.message);
    }
}

function updateSummary(data) {
    const avgWorkload = data.users.reduce((sum, user) => sum + user.workload, 0) / data.users.length;
    document.getElementById('avgWorkload').textContent = `${avgWorkload.toFixed(1)}%`;
    
    const overloaded = data.users.filter(user => user.workload > 100).length;
    document.getElementById('overloadedUsers').textContent = overloaded;
    
    const optimal = data.users.filter(user => user.workload >= 80 && user.workload <= 100).length;
    document.getElementById('optimalUsers').textContent = optimal;
}

function updateChart(data) {
    const users = data.users.sort((a, b) => b.workload - a.workload);
    
    workloadChart.data.labels = users.map(user => user.display_name || user.user_name);
    workloadChart.data.datasets[0].data = users.map(user => user.workload);
    workloadChart.data.datasets[0].backgroundColor = users.map(user => getWorkloadColor(user.workload));
    
    workloadChart.update();
}

function updateTable(data) {
    const tbody = document.querySelector('#workloadTable tbody');
    tbody.innerHTML = '';
    
    data.users.forEach(user => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${user.display_name || user.user_name}</td>
            <td>${user.team || '-'}</td>
            <td>${user.hours.toFixed(1)}</td>
            <td>${user.workload.toFixed(1)}%</td>
            <td>${getWorkloadStatus(user.workload)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function getWorkloadColor(workload) {
    if (workload > 100) return '#dc3545'; // czerwony
    if (workload >= 80) return '#28a745'; // zielony
    return '#ffc107'; // żółty
}

function getWorkloadStatus(workload) {
    if (workload > 100) {
        return '<span class="badge bg-danger">Przeciążenie</span>';
    }
    if (workload >= 80) {
        return '<span class="badge bg-success">Optymalnie</span>';
    }
    return '<span class="badge bg-warning text-dark">Niedociążenie</span>';
}

async function exportReport(format) {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const teamId = document.getElementById('teamSelect').value;
        
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate,
            format: format
        });
        if (teamId) params.append('team_id', teamId);
        
        const url = `/api/reports/export/workload?${params}`;
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