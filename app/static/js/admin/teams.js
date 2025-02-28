/**
 * Teams Management JavaScript
 * Handles team creation, editing, viewing and deletion
 */

// Dodajemy funkcję debugowania z zapisem do konsoli
function debug(message, obj = null) {
    if (typeof console !== 'undefined') {
        if (obj) {
            console.log(`[Teams Debug] ${message}`, obj);
        } else {
            console.log(`[Teams Debug] ${message}`);
        }
    }
}

$(document).ready(function() {
    debug('Document ready - initializing teams management');

    // Sprawdzamy, czy wszystkie niezbędne elementy istnieją
    const modalExists = $('#teamModal').length > 0;
    const formExists = $('#teamForm').length > 0;
    const selects = {
        leader: $('#leader_id').length > 0,
        members: $('#members').length > 0,
        projects: $('#projects').length > 0
    };

    debug('Elements check', {
        modalExists: modalExists,
        formExists: formExists,
        selects: selects
    });

    // Initialize Select2 for all dropdown selects - używam odpowiedniego motywu dla Bootstrap 5
    initializeSelect2();
    
    // Initialize DataTable
    $('#teamsTable').DataTable({
        responsive: true,
        order: [[0, 'asc']],
        pageLength: 25,
        columnDefs: [
            { orderable: false, targets: 4 }  // Disable sorting on Actions column
        ]
    });
    
    // Reset modal state when it's closed
    $('#teamModal').on('hidden.bs.modal', function() {
        debug('Modal hidden event triggered');
        resetTeamForm();
    });

    // Debugujemy otwarcie modala
    $('#teamModal').on('shown.bs.modal', function() {
        debug('Modal shown event triggered');
        // Sprawdzamy widoczność i interaktywność elementów
        const modal = $('#teamModal');
        const form = $('#teamForm');
        const nameInput = $('#name');
        
        debug('Modal visibility', {
            modalVisible: modal.is(':visible'),
            formVisible: form.is(':visible'),
            nameInputVisible: nameInput.is(':visible')
        });
        
        // Próba wymuszenia inicjalizacji Select2 po otwarciu modala
        initializeSelect2();
    });
    
    // Form validation on submit
    $('#saveTeamBtn').on('click', function(e) {
        debug('Save button clicked');
        e.preventDefault();
        
        // Validate form before submitting
        if (validateTeamForm()) {
            saveTeam();
        }
    });
});

/**
 * Initializes Select2 plugins for dropdowns
 */
function initializeSelect2() {
    debug('Initializing Select2');
    
    try {
        // Initialize Select2 for leader selection
        $('#leader_id').select2({
            theme: 'bootstrap-5',  // Używam motywu bootstrap-5 zamiast bootstrap4
            width: '100%',
            placeholder: 'Select Leader',
            allowClear: true,
            dropdownParent: $('#teamModal')  // Ważne: upewnia się, że dropdown pojawia się wewnątrz modala
        });
    
        // Initialize Select2 for members selection
        $('#members').select2({
            theme: 'bootstrap-5',  // Używam motywu bootstrap-5 zamiast bootstrap4
            width: '100%',
            placeholder: 'Select Members',
            allowClear: true,
            multiple: true,
            dropdownParent: $('#teamModal')  // Ważne: upewnia się, że dropdown pojawia się wewnątrz modala
        });
    
        // Initialize Select2 for projects selection
        $('#projects').select2({
            theme: 'bootstrap-5',  // Używam motywu bootstrap-5 zamiast bootstrap4
            width: '100%',
            placeholder: 'Select Projects',
            allowClear: true,
            multiple: true,
            dropdownParent: $('#teamModal')  // Ważne: upewnia się, że dropdown pojawia się wewnątrz modala
        });
        
        debug('Select2 initialization completed successfully');
    } catch (error) {
        debug('Error initializing Select2', error);
    }
}

/**
 * Resets the team form to default state
 */
function resetTeamForm() {
    debug('Resetting form');
    try {
        // Reset form and clear data attributes
        document.getElementById('teamForm').reset();
        $('#teamForm').removeData('team-id');
        
        // Clear validation states
        $('#teamForm .is-invalid').removeClass('is-invalid');
        
        // Reset Select2 elements
        $('#leader_id').val('').trigger('change');
        $('#members').val([]).trigger('change');
        $('#projects').val([]).trigger('change');
        
        // Reset modal title
        $('.modal-title').text('Add Team');
        
        debug('Form reset completed');
    } catch (error) {
        debug('Error resetting form', error);
    }
}

/**
 * Validates the team form
 * @returns {boolean} Whether the form is valid
 */
function validateTeamForm() {
    let isValid = true;
    const nameField = $('#name');
    
    // Validate name (required)
    if (!nameField.val().trim()) {
        nameField.addClass('is-invalid');
        isValid = false;
    } else {
        nameField.removeClass('is-invalid');
    }
    
    return isValid;
}

/**
 * Shows team details in a modal
 * @param {number} teamId - The ID of the team to view
 */
function viewTeam(teamId) {
    // Reset modal content
    $('#teamMembers').empty();
    $('#teamProjects').empty();
    
    // Add loading indicators
    $('#teamMembers').html('<li class="list-group-item text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Loading members...</li>');
    $('#teamProjects').html('<li class="list-group-item text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Loading projects...</li>');
    
    // Show modal with loading state
    $('#teamViewModal').modal('show');
    
    // Fetch team data
    fetch(`/admin/teams/${teamId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load team data');
            }
            return response.json();
        })
        .then(data => {
            // Clear loading indicators
            $('#teamMembers').empty();
            $('#teamProjects').empty();
            
            // Update modal title with team name
            $('#teamViewModalLabel').text(`Team Details: ${data.name}`);
            
            // Populate members
            if (data.members && data.members.length > 0) {
                data.members.forEach(member => {
                    $('#teamMembers').append(`
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            ${member.display_name || member.username}
                            ${member.id === data.leader_id ? '<span class="badge bg-primary">Leader</span>' : ''}
                        </li>
                    `);
                });
            } else {
                $('#teamMembers').append('<li class="list-group-item text-muted">No members assigned</li>');
            }
            
            // Populate projects
            if (data.projects && data.projects.length > 0) {
                data.projects.forEach(project => {
                    $('#teamProjects').append(`
                        <li class="list-group-item">
                            ${project.name}
                        </li>
                    `);
                });
            } else {
                $('#teamProjects').append('<li class="list-group-item text-muted">No projects assigned</li>');
            }
        })
        .catch(error => {
            // Clear loading indicators and show error
            $('#teamMembers').empty();
            $('#teamProjects').empty();
            
            $('#teamMembers').append('<li class="list-group-item text-danger">Error loading members</li>');
            $('#teamProjects').append('<li class="list-group-item text-danger">Error loading projects</li>');
            
            console.error('Error fetching team data:', error);
            
            // Show error notification
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: error.message || 'Failed to load team data'
            });
        });
}

/**
 * Opens the edit team modal for a specific team
 * @param {number} teamId - The ID of the team to edit
 */
function editTeam(teamId) {
    // Reset form first
    resetTeamForm();
    
    // Update modal title
    $('.modal-title').text('Edit Team');
    
    // Add loading state to save button
    const saveBtn = $('#saveTeamBtn');
    saveBtn.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...');
    saveBtn.prop('disabled', true);
    
    // Show modal with loading state
    $('#teamModal').modal('show');
    
    // Fetch team data
    fetch(`/admin/teams/${teamId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load team data');
            }
            return response.json();
        })
        .then(data => {
            // Store team ID for form submission
            $('#teamForm').data('team-id', teamId);
            
            // Set form values
            $('#name').val(data.name);
            $('#description').val(data.description);
            
            // Set leader
            if (data.leader_id) {
                $('#leader_id').val(data.leader_id).trigger('change');
            }
            
            // Set members
            if (data.members && data.members.length > 0) {
                const memberIds = data.members.map(m => m.id);
                $('#members').val(memberIds).trigger('change');
            }
            
            // Set projects
            if (data.projects && data.projects.length > 0) {
                const projectIds = data.projects.map(p => p.id);
                $('#projects').val(projectIds).trigger('change');
            }
            
            // Reset save button
            saveBtn.html('Save Team');
            saveBtn.prop('disabled', false);
        })
        .catch(error => {
            console.error('Error loading team data:', error);
            
            // Close modal and show error
            $('#teamModal').modal('hide');
            
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: error.message || 'Failed to load team data'
            });
        });
}

/**
 * Deletes a team after confirmation
 * @param {number} teamId - The ID of the team to delete
 */
function deleteTeam(teamId) {
    Swal.fire({
        title: 'Delete Team?',
        text: "This action cannot be undone.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Yes, delete it',
        cancelButtonText: 'Cancel'
    }).then((result) => {
        if (result.isConfirmed) {
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            // Send delete request
            fetch(`/admin/teams/${teamId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { 
                        throw new Error(err.message || 'Server error'); 
                    });
                }
                return response.json();
            })
            .then(data => {
                Swal.fire({
                    icon: 'success',
                    title: 'Deleted!',
                    text: data.message || 'Team has been deleted',
                    timer: 1500
                }).then(() => {
                    // Reload the page
                    window.location.reload();
                });
            })
            .catch(error => {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: error.message || 'Failed to delete team'
                });
                console.error('Error deleting team:', error);
            });
        }
    });
}

/**
 * Saves a team (create or update)
 */
function saveTeam() {
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    // Get team ID (if editing)
    const teamId = $('#teamForm').data('team-id');
    
    // Get form data
    const formData = {
        name: $('#name').val().trim(),
        description: $('#description').val().trim(),
        leader_id: $('#leader_id').val(),
        members: $('#members').val() || [],
        projects: $('#projects').val() || []
    };
    
    // Set button to loading state
    const saveBtn = $('#saveTeamBtn');
    const originalBtnText = saveBtn.html();
    saveBtn.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...');
    saveBtn.prop('disabled', true);
    
    // Determine if this is a create or update
    const isUpdate = !!teamId;
    const url = isUpdate ? `/admin/teams/${teamId}` : '/admin/teams/create';
    const method = isUpdate ? 'PUT' : 'POST';
    
    // Send request
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { 
                throw new Error(err.message || 'Server error'); 
            });
        }
        return response.json();
    })
    .then(data => {
        // Reset button state
        saveBtn.html(originalBtnText);
        saveBtn.prop('disabled', false);
        
        // Close modal
        $('#teamModal').modal('hide');
        
        // Show success message
        Swal.fire({
            icon: 'success',
            title: 'Success',
            text: data.message || `Team ${isUpdate ? 'updated' : 'created'} successfully`,
            timer: 1500
        }).then(() => {
            // Reload the page
            window.location.reload();
        });
    })
    .catch(error => {
        // Reset button state
        saveBtn.html(originalBtnText);
        saveBtn.prop('disabled', false);
        
        // Show error message
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: error.message || 'Failed to save team'
        });
        
        console.error('Error saving team:', error);
    });
} 