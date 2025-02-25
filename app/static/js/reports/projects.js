let projectsChart = null;
let usersChart = null;

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
    // Wykres projektów
    const projectsCtx = document.getElementById('projectsChart').getContext('2d');
    projectsChart = new Chart(projectsCtx, {
        type: 'pie',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'rgb(255, 99, 132)',
                    'rgb(54, 162, 235)',
                    'rgb(255, 205, 86)',
                    'rgb(75, 192, 192)',
                    'rgb(153, 102, 255)',
                    'rgb(255, 159, 64)'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Podział godzin na projekty'
                }
            }
        }
    });

    // Wykres użytkowników
    const usersCtx = document.getElementById('usersChart').getContext('2d');
    usersChart = new Chart(usersCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Godziny na projekt',
                data: [],
                backgroundColor: 'rgb(54, 162, 235)'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Top użytkownicy'
                }
            }
        }
    });
}

async function loadReport() {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        const response = await fetch(`/api/reports/projects?start_date=${startDate}&end_date=${endDate}`);
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
    document.getElementById('totalProjects').textContent = Object.keys(report.projects).length;
    document.getElementById('totalTasks').textContent = report.total_tasks;
}

function updateCharts(report) {
    // Aktualizacja wykresu projektów
    const projects = Object.keys(report.projects);
    const projectHours = projects.map(project => report.projects[project].total_hours);
    
    projectsChart.data.labels = projects;
    projectsChart.data.datasets[0].data = projectHours;
    projectsChart.update();
    
    // Aktualizacja wykresu użytkowników
    const userStats = {};
    for (const project in report.projects) {
        for (const user in report.projects[project].users) {
            if (!userStats[user]) {
                userStats[user] = 0;
            }
            userStats[user] += report.projects[project].users[user].hours;
        }
    }
    
    const sortedUsers = Object.entries(userStats)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 10);
    
    usersChart.data.labels = sortedUsers.map(([user]) => user);
    usersChart.data.datasets[0].data = sortedUsers.map(([,hours]) => hours);
    usersChart.update();
}

function updateTable(report) {
    const tbody = document.querySelector('#projectsTable tbody');
    tbody.innerHTML = '';
    
    for (const project in report.projects) {
        const projectData = report.projects[project];
        for (const user in projectData.users) {
            const userData = projectData.users[user];
            const percentage = (userData.hours / projectData.total_hours * 100).toFixed(1);
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${project}</td>
                <td>${user}</td>
                <td>${userData.hours.toFixed(1)}</td>
                <td>${userData.tasks}</td>
                <td>${percentage}%</td>
            `;
            tbody.appendChild(tr);
        }
    }
}

async function exportReport(format) {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        const url = `/api/reports/export/projects?start_date=${startDate}&end_date=${endDate}&format=${format}`;
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