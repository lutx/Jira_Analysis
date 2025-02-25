let currentTeamId = null;

document.addEventListener('DOMContentLoaded', function() {
    loadTeams();
    loadUsers();
});

async function loadTeams() {
    try {
        const response = await fetch('/api/teams');
        const teams = await response.json();
        
        const tbody = document.querySelector('#teamsTable tbody');
        tbody.innerHTML = '';
        
        teams.forEach(team => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${team.name}</td>
                <td>${team.description || '-'}</td>
                <td>${team.leader_id || '-'}</td>
                <td>${team.members.length} członków</td>
                <td>
                    <span class="badge ${team.is_active ? 'bg-success' : 'bg-danger'}">
                        ${team.is_active ? 'Aktywny' : 'Nieaktywny'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary me-1" onclick="editTeam(${team.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-info me-1" onclick="manageMembers(${team.id})">
                        <i class="bi bi-people"></i>
                    </button>
                    <button class="btn btn-sm ${team.is_active ? 'btn-danger' : 'btn-success'}" 
                            onclick="toggleTeamStatus(${team.id}, ${team.is_active})">
                        <i class="bi ${team.is_active ? 'bi-x-circle' : 'bi-check-circle'}"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading teams:', error);
        showError('Błąd podczas ładowania zespołów');
    }
}

async function loadUsers() {
    try {
        const response = await fetch('/api/users');
        const users = await response.json();
        
        const leaderSelect = document.getElementById('teamLeader');
        const memberSelect = document.getElementById('newMember');
        
        users.forEach(user => {
            const option = new Option(user.display_name || user.user_name, user.user_name);
            leaderSelect.add(option.cloneNode(true));
            memberSelect.add(option);
        });
    } catch (error) {
        console.error('Error loading users:', error);
        showError('Błąd podczas ładowania użytkowników');
    }
}

function editTeam(teamId) {
    currentTeamId = teamId;
    
    fetch(`/api/teams/${teamId}`)
        .then(response => response.json())
        .then(team => {
            document.getElementById('teamId').value = team.id;
            document.getElementById('teamName').value = team.name;
            document.getElementById('teamDescription').value = team.description;
            document.getElementById('teamLeader').value = team.leader_id;
            
            const modal = new bootstrap.Modal(document.getElementById('teamModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading team details:', error);
            showError('Błąd podczas ładowania szczegółów zespołu');
        });
}

async function saveTeam() {
    try {
        const data = {
            name: document.getElementById('teamName').value,
            description: document.getElementById('teamDescription').value,
            leader_id: document.getElementById('teamLeader').value
        };
        
        const method = currentTeamId ? 'PUT' : 'POST';
        const url = currentTeamId ? `/api/teams/${currentTeamId}` : '/api/teams';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        bootstrap.Modal.getInstance(document.getElementById('teamModal')).hide();
        document.getElementById('teamForm').reset();
        currentTeamId = null;
        
        loadTeams();
        showSuccess('Zespół został zapisany');
    } catch (error) {
        console.error('Error saving team:', error);
        showError('Błąd podczas zapisywania zespołu');
    }
}

function manageMembers(teamId) {
    currentTeamId = teamId;
    
    fetch(`/api/teams/${teamId}`)
        .then(response => response.json())
        .then(team => {
            const tbody = document.querySelector('#membersTable tbody');
            tbody.innerHTML = '';
            
            team.members.forEach(member => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${member.display_name || member.user_name}</td>
                    <td>${member.role}</td>
                    <td>${new Date(member.joined_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="removeMember('${member.user_name}')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            
            const modal = new bootstrap.Modal(document.getElementById('membersModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading team members:', error);
            showError('Błąd podczas ładowania członków zespołu');
        });
}

async function addMember() {
    try {
        const userName = document.getElementById('newMember').value;
        if (!userName) return;
        
        const response = await fetch(`/api/teams/${currentTeamId}/members`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_name: userName })
        });
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        document.getElementById('newMember').value = '';
        manageMembers(currentTeamId);
        showSuccess('Użytkownik został dodany do zespołu');
    } catch (error) {
        console.error('Error adding team member:', error);
        showError('Błąd podczas dodawania członka zespołu');
    }
}

async function removeMember(userName) {
    if (!confirm('Czy na pewno chcesz usunąć tego użytkownika z zespołu?')) return;
    
    try {
        const response = await fetch(`/api/teams/${currentTeamId}/members/${userName}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        manageMembers(currentTeamId);
        showSuccess('Użytkownik został usunięty z zespołu');
    } catch (error) {
        console.error('Error removing team member:', error);
        showError('Błąd podczas usuwania członka zespołu');
    }
}

async function toggleTeamStatus(teamId, currentStatus) {
    try {
        const response = await fetch(`/api/teams/${teamId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_active: !currentStatus })
        });
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        loadTeams();
        showSuccess(`Zespół został ${currentStatus ? 'dezaktywowany' : 'aktywowany'}`);
    } catch (error) {
        console.error('Error toggling team status:', error);
        showError('Błąd podczas zmiany statusu zespołu');
    }
}

function showSuccess(message) {
    // Implementacja wyświetlania sukcesu
    alert(message);
}

function showError(message) {
    // Implementacja wyświetlania błędu
    alert(message);
} 