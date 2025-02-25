document.addEventListener('DOMContentLoaded', function() {
    // Initialize any report-specific components
    initializeCharts();
});

function initializeCharts() {
    // Initialize charts if they exist on the page
    const chartElements = document.querySelectorAll('.chart-container');
    chartElements.forEach(container => {
        const chartType = container.dataset.chartType;
        const chartData = JSON.parse(container.dataset.chartData);
        
        switch(chartType) {
            case 'workload':
                createWorkloadChart(container, chartData);
                break;
            case 'roles':
                createRolesChart(container, chartData);
                break;
            case 'availability':
                createAvailabilityChart(container, chartData);
                break;
            case 'shadow':
                createShadowWorkChart(container, chartData);
                break;
        }
    });
}

function createWorkloadChart(container, data) {
    new Chart(container.querySelector('canvas'), {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Workload Distribution'
                }
            }
        }
    });
}

function createRolesChart(container, data) {
    new Chart(container.querySelector('canvas'), {
        type: 'pie',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Role Distribution'
                }
            }
        }
    });
}

function createAvailabilityChart(container, data) {
    new Chart(container.querySelector('canvas'), {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'User Availability'
                }
            }
        }
    });
}

function createShadowWorkChart(container, data) {
    new Chart(container.querySelector('canvas'), {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Shadow Work Analysis'
                }
            }
        }
    });
}

function exportReport(format) {
    const reportType = document.querySelector('.report-container').dataset.reportType;
    
    fetch(`/admin/reports/export/${reportType}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({ format })
    })
    .then(response => {
        if (format === 'excel' || format === 'pdf' || format === 'csv') {
            return response.blob();
        }
        return response.json();
    })
    .then(data => {
        if (data instanceof Blob) {
            const url = window.URL.createObjectURL(data);
            const a = document.createElement('a');
            a.href = url;
            a.download = `report.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } else {
            showNotification(data.message, data.status);
        }
    })
    .catch(error => {
        console.error('Error exporting report:', error);
        showNotification('Error exporting report', 'error');
    });
} 