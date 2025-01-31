// Funkcja do usuwania portfolio
async function deletePortfolio(portfolioId) {
    try {
        // Najpierw sprawdź czy potrzebne jest potwierdzenie
        const checkResponse = await fetch(`/api/portfolios/${portfolioId}`, {
            method: 'DELETE'
        });
        
        const data = await checkResponse.json();
        
        // Jeśli wymagane jest potwierdzenie
        if (checkResponse.status === 409 && data.code === 'CONFIRMATION_REQUIRED') {
            Swal.fire({
                title: 'Potwierdzenie usunięcia',
                text: data.message,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#d33',
                cancelButtonColor: '#3085d6',
                confirmButtonText: 'Tak, usuń',
                cancelButtonText: 'Anuluj'
            }).then(async (result) => {
                if (result.isConfirmed) {
                    // Wykonaj usunięcie z potwierdzeniem
                    const deleteResponse = await fetch(`/api/portfolios/${portfolioId}?confirm=true`, {
                        method: 'DELETE'
                    });
                    
                    const deleteData = await deleteResponse.json();
                    
                    if (deleteResponse.ok) {
                        Swal.fire(
                            'Usunięto!',
                            deleteData.message,
                            'success'
                        );
                        // Odśwież listę portfoliów
                        loadPortfolios();
                    } else {
                        throw new Error(deleteData.error || 'Błąd podczas usuwania portfolio');
                    }
                }
            });
        } else if (checkResponse.ok) {
            // Jeśli nie było wymagane potwierdzenie i usunięcie się powiodło
            Swal.fire(
                'Usunięto!',
                data.message,
                'success'
            );
            // Odśwież listę portfoliów
            loadPortfolios();
        } else {
            throw new Error(data.error || 'Błąd podczas usuwania portfolio');
        }
    } catch (error) {
        console.error('Error:', error);
        Swal.fire(
            'Błąd!',
            error.message,
            'error'
        );
    }
}

// Funkcja do wyświetlania szczegółów dla superadmina
function showDeletionDetails(details) {
    if (details) {
        Swal.fire({
            title: 'Szczegóły usunięcia',
            html: `
                <p>Portfolio: ${details.portfolio_name}</p>
                <p>Usunięte projekty: ${details.deleted_projects}</p>
            `,
            icon: 'info'
        });
    }
}

// Dodaj obsługę przycisku usuwania w HTML
function createDeleteButton(portfolioId) {
    return `
        <button 
            class="btn btn-sm btn-outline-danger" 
            onclick="deletePortfolio(${portfolioId})"
            title="Usuń portfolio"
        >
            <i class="bi bi-trash"></i>
        </button>
    `;
}

// Funkcja ładująca listę portfoliów
async function loadPortfolios() {
    try {
        const response = await fetch('/api/portfolios');
        if (!response.ok) throw new Error('Błąd pobierania portfoliów');
        
        const portfolios = await response.json();
        const tbody = document.getElementById('portfoliosList');
        tbody.innerHTML = '';
        
        portfolios.forEach(portfolio => {
            tbody.innerHTML += `
                <tr>
                    <td>${portfolio.name}</td>
                    <td>${portfolio.project_count}</td>
                    <td>${portfolio.active_projects}</td>
                    <td>
                        <div class="btn-group">
                            <button 
                                class="btn btn-sm btn-outline-primary" 
                                onclick="editPortfolio(${portfolio.id})"
                                title="Edytuj portfolio"
                            >
                                <i class="bi bi-pencil"></i>
                            </button>
                            ${createDeleteButton(portfolio.id)}
                            <button 
                                class="btn btn-sm btn-outline-success" 
                                onclick="manageProjects(${portfolio.id})"
                                title="Zarządzaj projektami"
                            >
                                <i class="bi bi-folder"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });
    } catch (error) {
        console.error('Error:', error);
        Swal.fire('Błąd!', error.message, 'error');
    }
}

// Funkcja pokazująca modal dodawania portfolio
function showAddPortfolioModal() {
    document.getElementById('portfolioModalTitle').textContent = 'Dodaj Portfolio';
    document.getElementById('portfolioForm').reset();
    document.getElementById('portfolioForm').dataset.mode = 'add';
    new bootstrap.Modal(document.getElementById('portfolioModal')).show();
}

// Funkcja zapisująca portfolio
async function savePortfolio() {
    try {
        const form = document.getElementById('portfolioForm');
        const name = document.getElementById('portfolioName').value;
        const mode = form.dataset.mode;
        
        const response = await fetch('/api/portfolios' + (mode === 'edit' ? `/${form.dataset.portfolioId}` : ''), {
            method: mode === 'edit' ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name })
        });
        
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.error);
        
        bootstrap.Modal.getInstance(document.getElementById('portfolioModal')).hide();
        await loadPortfolios();
        
        Swal.fire('Sukces!', data.message, 'success');
    } catch (error) {
        console.error('Error:', error);
        Swal.fire('Błąd!', error.message, 'error');
    }
}

// Funkcja edycji portfolio
async function editPortfolio(portfolioId) {
    try {
        const response = await fetch(`/api/portfolios/${portfolioId}`);
        if (!response.ok) throw new Error('Błąd pobierania danych portfolio');
        
        const portfolio = await response.json();
        
        document.getElementById('portfolioModalTitle').textContent = 'Edytuj Portfolio';
        document.getElementById('portfolioName').value = portfolio.name;
        document.getElementById('portfolioForm').dataset.mode = 'edit';
        document.getElementById('portfolioForm').dataset.portfolioId = portfolioId;
        
        new bootstrap.Modal(document.getElementById('portfolioModal')).show();
    } catch (error) {
        console.error('Error:', error);
        Swal.fire('Błąd!', error.message, 'error');
    }
}

// Funkcja zarządzania projektami
function manageProjects(portfolioId) {
    window.location.href = `/admin/portfolios/${portfolioId}/projects`;
} 