document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const teamsTable = $('#teamsTable').DataTable({
        pageLength: 10,
        order: [[0, 'asc']]
    });
    
    // Initialize Select2 for members and projects
    $('.select2').select2({
        theme: 'bootstrap4',
        width: '100%'
    });
});

function viewTeam(teamId) {
    fetch(`/admin/teams/${teamId}`)
        .then(response => response.json())
        .then(team => {
            $('#teamViewModal').modal('show');
            
            // Fill members list
            const membersList = $('#teamMembers');
            membersList.empty();
            team.members.forEach(member => {
                membersList.append(`
                    <li class="list-group-item">
                        ${member.display_name} (${member.email})
                    </li>
                `);
            });
            
            // Fill projects list
            const projectsList = $('#teamProjects');
            projectsList.empty();
            team.projects.forEach(project => {
                projectsList.append(`
                    <li class="list-group-item">
                        ${project.name}
                    </li>
                `);
            });
        })
        .catch(error => {
            console.error('Error loading team:', error);
            showNotification('Error loading team data', 'error');
        });
}

function editTeam(teamId) {
    fetch(`/admin/teams/${teamId}`)
        .then(response => response.json())
        .then(team => {
            $('#teamForm')[0].reset();
            $('#teamModal').modal('show');
            $('#teamForm [name=name]').val(team.name);
            $('#teamForm [name=description]').val(team.description);
            $('#teamForm [name=members]').val(team.members.map(m => m.id)).trigger('change');
            $('#teamForm [name=projects]').val(team.projects.map(p => p.id)).trigger('change');
            $('#teamForm').data('teamId', teamId);
            $('.modal-title').text('Edit Team');
        })
        .catch(error => {
            console.error('Error loading team:', error);
            showNotification('Error loading team data', 'error');
        });
}

function saveTeam() {
    const form = $('#teamForm');
    const teamId = form.data('teamId');
    const data = {
        name: form.find('[name=name]').val(),
        description: form.find('[name=description]').val(),
        members: form.find('[name=members]').val(),
        projects: form.find('[name=projects]').val()
    };
    
    const url = teamId ? `/admin/teams/${teamId}` : '/admin/teams';
    const method = teamId ? 'PUT' : 'POST';
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            $('#teamModal').modal('hide');
            showNotification(result.message, 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving team:', error);
        showNotification('Error saving team', 'error');
    });
}

function deleteTeam(teamId) {
    if (confirm('Are you sure you want to delete this team?')) {
        fetch(`/admin/teams/${teamId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                showNotification(result.message, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(result.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting team:', error);
            showNotification('Error deleting team', 'error');
        });
    }
} 