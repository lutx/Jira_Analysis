console.log('Projects script loaded');

document.addEventListener('DOMContentLoaded', function() {
    const syncButton = document.querySelector('#syncProjects');
    console.log('Sync button:', syncButton);

    if (syncButton) {
        syncButton.addEventListener('click', async function() {
            console.log('Sync button clicked');
            
            // Zapisz oryginalny tekst przycisku przed zmianami
            const originalButtonText = syncButton.innerHTML;
            
            try {
                // Pokaż loading
                syncButton.disabled = true;
                syncButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Synchronizacja...';

                // Pobierz CSRF token
                const metaTag = document.querySelector('meta[name="csrf-token"]');
                if (!metaTag) {
                    throw new Error('Brak tokena CSRF');
                }
                const csrfToken = metaTag.getAttribute('content');

                // Wykonaj request
                const response = await fetch('/admin/api/projects/sync', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                });

                console.log('Response:', response);

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                
                if (data.status === 'success') {
                    // Użyj SweetAlert2 zamiast toastr, jeśli toastr nie jest dostępny
                    if (typeof toastr !== 'undefined') {
                        toastr.success(data.message);
                    } else {
                        Swal.fire({
                            icon: 'success',
                            title: 'Sukces!',
                            text: data.message
                        });
                    }
                    setTimeout(() => location.reload(), 2000);
                } else {
                    throw new Error(data.message || 'Wystąpił błąd podczas synchronizacji');
                }

            } catch (error) {
                console.error('Error:', error);
                // Użyj SweetAlert2 zamiast toastr, jeśli toastr nie jest dostępny
                if (typeof toastr !== 'undefined') {
                    toastr.error(error.message || 'Wystąpił błąd podczas synchronizacji projektów');
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Błąd!',
                        text: error.message || 'Wystąpił błąd podczas synchronizacji projektów'
                    });
                }
            } finally {
                // Przywróć przycisk do stanu początkowego
                syncButton.disabled = false;
                syncButton.innerHTML = originalButtonText;
            }
        });
    }

    // Initialize DataTable
    const projectsTable = $('#projectsTable').DataTable({
        pageLength: 10,
        order: [[0, 'asc']]
    });
    
    // Initialize Select2 for teams
    $('.select2').select2({
        theme: 'bootstrap4',
        width: '100%'
    });
});

function viewProject(projectId) {
    fetch(`/admin/projects/${projectId}`)
        .then(response => response.json())
        .then(project => {
            $('#projectViewModal').modal('show');
            
            // Fill teams list
            const teamsList = $('#projectTeams');
            teamsList.empty();
            project.teams.forEach(team => {
                teamsList.append(`
                    <li class="list-group-item">
                        ${team.name}
                    </li>
                `);
            });
            
            // Fill statistics
            const statsList = $('#projectStats');
            statsList.empty();
            statsList.append(`
                <li class="list-group-item">
                    <strong>Total Hours:</strong> ${project.total_hours}
                </li>
                <li class="list-group-item">
                    <strong>Active Users:</strong> ${project.active_users_count}
                </li>
                <li class="list-group-item">
                    <strong>Last Update:</strong> ${project.updated_at}
                </li>
            `);
        })
        .catch(error => {
            console.error('Error loading project:', error);
            showNotification('Error loading project data', 'error');
        });
}

function editProject(projectId) {
    fetch(`/admin/projects/${projectId}`)
        .then(response => response.json())
        .then(project => {
            $('#projectForm')[0].reset();
            $('#projectModal').modal('show');
            $('#projectForm [name=name]').val(project.name);
            $('#projectForm [name=jira_key]').val(project.jira_key);
            $('#projectForm [name=description]').val(project.description);
            $('#projectForm [name=teams]').val(project.teams.map(t => t.id)).trigger('change');
            $('#projectForm [name=status]').val(project.status);
            $('#projectForm').data('projectId', projectId);
            $('.modal-title').text('Edit Project');
        })
        .catch(error => {
            console.error('Error loading project:', error);
            showNotification('Error loading project data', 'error');
        });
}

function saveProject() {
    const form = $('#projectForm');
    const projectId = form.data('projectId');
    const data = {
        name: form.find('[name=name]').val(),
        jira_key: form.find('[name=jira_key]').val(),
        description: form.find('[name=description]').val(),
        teams: form.find('[name=teams]').val(),
        status: form.find('[name=status]').val()
    };
    
    const url = projectId ? `/admin/projects/${projectId}` : '/admin/projects';
    const method = projectId ? 'PUT' : 'POST';
    
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
            $('#projectModal').modal('hide');
            showNotification(result.message, 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving project:', error);
        showNotification('Error saving project', 'error');
    });
}

function deleteProject(projectId) {
    if (confirm('Are you sure you want to delete this project?')) {
        fetch(`/admin/projects/${projectId}`, {
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
            console.error('Error deleting project:', error);
            showNotification('Error deleting project', 'error');
        });
    }
}

function syncJiraProjects() {
    fetch('/admin/projects/sync', {
        method: 'POST',
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
        console.error('Error syncing projects:', error);
        showNotification('Error syncing with JIRA', 'error');
    });
} 