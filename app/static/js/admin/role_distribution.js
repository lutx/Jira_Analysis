document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const roleTable = $('#roleTable').DataTable({
        pageLength: 25,
        order: [[1, 'desc']]
    });
    
    // Handle filter form submit
    $('#roleFilters').on('submit', function(e) {
        e.preventDefault();
        updateRoleData();
    });
});

function updateRoleData() {
    const filters = {
        team_id: $('[name=team_id]').val(),
        project_id: $('[name=project_id]').val()
    };
    
    fetch('/admin/reports/roles/data?' + new URLSearchParams(filters))
        .then(response => response.json())
        .then(data => {
            // Update overall role chart
            updateChart(
                document.querySelector('[data-chart-type="roles"]:first-child'),
                data.overall_role_data
            );
            
            // Update team role chart
            updateChart(
                document.querySelector('[data-chart-type="roles"]:last-child'),
                data.team_role_data
            );
            
            // Update role details table
            updateTable(data.role_details);
        })
        .catch(error => {
            console.error('Error updating role data:', error);
            showNotification('Error updating role distribution data', 'error');
        });
}

function updateChart(container, data) {
    const chart = Chart.getChart(container.querySelector('canvas'));
    if (chart) {
        chart.data = data;
        chart.update();
    } else {
        createRolesChart(container, data);
    }
}

function updateTable(data) {
    const table = $('#roleTable').DataTable();
    table.clear();
    
    data.forEach(role => {
        table.row.add([
            role.name,
            role.users_count,
            role.teams_count,
            role.projects_count,
            `<div class="progress">
                <div class="progress-bar" 
                     role="progressbar" 
                     style="width: ${role.distribution}%">
                    ${role.distribution}%
                </div>
            </div>`
        ]);
    });
    
    table.draw();
} 