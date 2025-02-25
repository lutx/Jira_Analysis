document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const workloadTable = $('#workloadTable').DataTable({
        pageLength: 25,
        order: [[1, 'desc']]
    });
    
    // Initialize DateRangePicker
    $('.daterange').daterangepicker({
        opens: 'left',
        locale: {
            format: 'YYYY-MM-DD'
        },
        ranges: {
            'Today': [moment(), moment()],
            'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        }
    });
    
    // Handle filter form submit
    $('#workloadFilters').on('submit', function(e) {
        e.preventDefault();
        updateWorkloadData();
    });
});

function updateWorkloadData() {
    const filters = {
        team_id: $('[name=team_id]').val(),
        project_id: $('[name=project_id]').val(),
        date_range: $('[name=date_range]').val()
    };
    
    fetch('/admin/reports/workload/data?' + new URLSearchParams(filters))
        .then(response => response.json())
        .then(data => {
            // Update team workload chart
            updateChart(
                document.querySelector('[data-chart-type="workload"]:first-child'),
                data.team_workload
            );
            
            // Update user workload chart
            updateChart(
                document.querySelector('[data-chart-type="workload"]:last-child'),
                data.user_workload
            );
            
            // Update detailed stats table
            updateTable(data.detailed_stats);
        })
        .catch(error => {
            console.error('Error updating workload data:', error);
            showNotification('Error updating workload data', 'error');
        });
}

function updateChart(container, data) {
    const chart = Chart.getChart(container.querySelector('canvas'));
    if (chart) {
        chart.data = data;
        chart.update();
    } else {
        createWorkloadChart(container, data);
    }
}

function updateTable(data) {
    const table = $('#workloadTable').DataTable();
    table.clear();
    
    data.forEach(stat => {
        table.row.add([
            stat.name,
            stat.total_hours,
            stat.projects_count,
            stat.avg_daily_hours,
            `<div class="progress">
                <div class="progress-bar bg-${getUtilizationClass(stat.utilization)}" 
                     role="progressbar" 
                     style="width: ${stat.utilization}%">
                    ${stat.utilization}%
                </div>
            </div>`
        ]);
    });
    
    table.draw();
}

function getUtilizationClass(utilization) {
    if (utilization < 80) return 'success';
    if (utilization < 100) return 'warning';
    return 'danger';
} 