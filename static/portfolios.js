document.addEventListener('DOMContentLoaded', function() {
    loadPortfolios();
    
    // Obsługa formularza portfolio
    document.getElementById('savePortfolio').addEventListener('click', savePortfolio);
    document.getElementById('addProject').addEventListener('click', addProjectToPortfolio);
    
    // Obsługa modala
    const portfolioModal = new bootstrap.Modal(document.getElementById('portfolioModal'));
    
    // Czyszczenie formularza przy zamykaniu modala
    document.getElementById('portfolioModal').addEventListener('hidden.bs.modal', function () {
        document.getElementById('portfolioForm').reset();
        document.getElementById('portfolioId').value = '';
        document.querySelector('#projectsTable tbody').innerHTML = '';
    });
});

async function loadPortfolios() {
    try {
        const response = await fetch('/api/portfolios');
        const portfolios = await response.json();
        
        const tbody = document.querySelector('#portfoliosTable tbody');
        tbody.innerHTML = '';
        
        portfolios.forEach(portfolio => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${portfolio.name}</td>
                <td>${portfolio.projects_count}</td>
                <td>${portfolio.users_count}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="editPortfolio(${portfolio.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-info" onclick="manageProjects(${portfolio.id})">
                        <i class="bi bi-folder"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deletePortfolio(${portfolio.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading portfolios:', error);
        showError('Błąd podczas ładowania portfoliów');
    }
}

async function manageProjects(portfolioId) {
    try {
        const response = await fetch(`/api/portfolios/${portfolioId}/projects`);
        const data = await response.json();
        
        document.getElementById('portfolioId').value = portfolioId;
        document.getElementById('portfolioName').value = data.name;
        
        const tbody = document.querySelector('#projectsTable tbody');
        tbody.innerHTML = '';
        
        data.projects.forEach(project => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${project.key}</td>
                <td>${project.name}</td>
                <td><span class="badge ${project.active ? 'bg-success' : 'bg-secondary'}">
                    ${project.active ? 'Aktywny' : 'Nieaktywny'}
                </span></td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeProject('${project.key}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
        
        const modal = new bootstrap.Modal(document.getElementById('portfolioModal'));
        modal.show();
    } catch (error) {
        console.error('Error loading portfolio projects:', error);
        showError('Błąd podczas ładowania projektów portfolio');
    }
}

async function addProjectToPortfolio() {
    const projectKey = document.getElementById('projectKey').value.trim();
    if (!projectKey) {
        showError('Wprowadź klucz projektu');
        return;
    }
    
    const portfolioId = document.getElementById('portfolioId').value;
    
    try {
        const response = await fetch(`/api/portfolios/${portfolioId}/projects`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ project_key: projectKey })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Błąd podczas dodawania projektu');
        }
        
        document.getElementById('projectKey').value = '';
        await manageProjects(portfolioId);
        showSuccess('Projekt został dodany do portfolio');
    } catch (error) {
        console.error('Error adding project:', error);
        showError(error.message);
    }
}

async function removeProject(projectKey) {
    if (!confirm(`Czy na pewno chcesz usunąć projekt ${projectKey} z portfolio?`)) {
        return;
    }
    
    const portfolioId = document.getElementById('portfolioId').value;
    
    try {
        const response = await fetch(`/api/portfolios/${portfolioId}/projects/${projectKey}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Błąd podczas usuwania projektu');
        }
        
        await manageProjects(portfolioId);
        showSuccess('Projekt został usunięty z portfolio');
    } catch (error) {
        console.error('Error removing project:', error);
        showError(error.message);
    }
}

async function savePortfolio() {
    const portfolioId = document.getElementById('portfolioId').value;
    const name = document.getElementById('portfolioName').value;
    
    if (!name) {
        showError('Nazwa portfolio jest wymagana');
        return;
    }
    
    try {
        const url = portfolioId ? 
            `/api/portfolios/${portfolioId}` : 
            '/api/portfolios';
            
        const method = portfolioId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Błąd podczas zapisywania portfolio');
        }
        
        // Zamknij modal i odśwież listę
        const portfolioModal = bootstrap.Modal.getInstance(document.getElementById('portfolioModal'));
        portfolioModal.hide();
        
        loadPortfolios();
        showSuccess(portfolioId ? 'Portfolio zostało zaktualizowane' : 'Portfolio zostało dodane');
    } catch (error) {
        console.error('Error saving portfolio:', error);
        showError(error.message);
    }
}

async function editPortfolio(portfolioId) {
    const name = prompt('Podaj nową nazwę portfolio:');
    if (name === null) return;
    
    try {
        const response = await fetch(`/api/portfolios/${portfolioId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Błąd podczas aktualizacji portfolio');
        }
        
        loadPortfolios();
        showSuccess('Portfolio zostało zaktualizowane');
    } catch (error) {
        console.error('Error updating portfolio:', error);
        showError(error.message);
    }
}

async function deletePortfolio(portfolioId) {
    if (!confirm('Czy na pewno chcesz usunąć to portfolio?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/portfolios/${portfolioId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Błąd podczas usuwania portfolio');
        }
        
        loadPortfolios();
        showSuccess('Portfolio zostało usunięte');
    } catch (error) {
        console.error('Error deleting portfolio:', error);
        showError(error.message);
    }
}

function showSuccess(message) {
    alert(message); // Tymczasowo używamy alert
}

function showError(message) {
    alert(message); // Tymczasowo używamy alert
} 