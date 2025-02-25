document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const shadowWorkTable = $('#shadowWorkTable').DataTable({
        pageLength: 25,
        order: [[4, 'desc']]
    });
    
    // Initialize DateRangePicker
    $('.daterange').daterangepicker({
        opens: 'left',
        locale: {
            format: 'YYYY-MM-DD'
        },
        ranges: {
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        }
    });
    
    // Handle filter form submit
    $('#shadowWorkFilters').on('submit', function(e) {
        e.preventDefault();
        updateShadowWorkData();
    });
});

function updateShadowWorkData() {
    const filters = {
        team_id: $('[name=team_id]').val(),
        date_range: $('[name=date_range]').val(),
        category: $('[name=category]').val()
    };
    
    fetch('/admin/reports/shadow-work/data?' + new URLSearchParams(filters))
        .then(response => response.json())
        .then(data => {
            // Update summary cards
            updateSummaryCards(data.summary);
            
            // Update category distribution chart
            updateChart(
                document.querySelector('[data-chart-type="shadow"]:first-child'),
                data.category_distribution
            );
            
            // Update time trend chart
            updateChart(
                document.querySelector('[data-chart-type="shadow"]:last-child'),
                data.time_trend
            );
            
            // Update detailed table
            updateTable(data.shadow_work_details);
        })
        .catch(error => {
            console.error('Error updating shadow work data:', error);
            showNotification('Error updating shadow work data', 'error');
        });
}

function updateSummaryCards(summary) {
    document.querySelector('.bg-primary h3').textContent = summary.total_hours;
    document.querySelector('.bg-success h3').textContent = summary.avg_hours_per_user;
    document.querySelector('.bg-info h3').textContent = summary.most_common_category;
    document.querySelector('.bg-warning h3').textContent = summary.impact_percentage + '%';
}

function updateChart(container, data) {
    const chart = Chart.getChart(container.querySelector('canvas'));
    if (chart) {
        chart.data = data;
        chart.update();
    } else {
        createShadowWorkChart(container, data);
    }
}

function updateTable(data) {
    const table = $('#shadowWorkTable').DataTable();
    table.clear();
    
    data.forEach(entry => {
        table.row.add([
            entry.user.display_name,
            entry.team.name,
            `<span class="badge bg-${entry.category_class}">${entry.category}</span>`,
            entry.hours,
            entry.date,
            entry.description
        ]);
    });
    
    table.draw();
}

function getCategoryClass(category) {
    const classes = {
        'meetings': 'primary',
        'support': 'success',
        'maintenance': 'info',
        'other': 'secondary'
    };
    return classes[category.toLowerCase()] || 'secondary';
} 