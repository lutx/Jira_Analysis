document.addEventListener('DOMContentLoaded', function() {
    const portfolioModal = new bootstrap.Modal(document.getElementById('portfolioModal'));
    
    window.editPortfolio = function(id) {
        fetch(`/panel-admina/portfolios/${id}`)
            .then(response => response.json())
            .then(data => {
                document.getElementById('portfolioForm').reset();
                document.getElementById('portfolioModalTitle').textContent = 'Edytuj Portfolio';
                
                // Wypełnij formularz danymi
                const form = document.getElementById('portfolioForm');
                form.querySelector('[name="name"]').value = data.name;
                form.querySelector('[name="description"]').value = data.description;
                form.querySelector('[name="is_active"]').checked = data.is_active;
                
                // Zaznacz projekty
                const projectSelect = form.querySelector('[name="projects"]');
                if (projectSelect) {
                    Array.from(projectSelect.options).forEach(option => {
                        option.selected = data.project_ids.includes(parseInt(option.value));
                    });
                }
                
                portfolioModal.show();
            })
            .catch(error => {
                showNotification('Błąd podczas ładowania danych portfolio', 'danger');
            });
    };
    
    window.deletePortfolio = function(id) {
        if (confirm('Czy na pewno chcesz usunąć to portfolio?')) {
            fetch(`/panel-admina/portfolios/${id}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                }
            })
            .then(response => {
                if (response.ok) {
                    location.reload();
                } else {
                    throw new Error('Błąd podczas usuwania portfolio');
                }
            })
            .catch(error => {
                showNotification('Błąd podczas usuwania portfolio', 'danger');
            });
        }
    };
    
    window.savePortfolio = function() {
        const form = document.getElementById('portfolioForm');
        const formData = new FormData(form);
        
        fetch('/panel-admina/portfolios', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: formData
        })
        .then(response => {
            if (response.ok) {
                portfolioModal.hide();
                location.reload();
            } else {
                throw new Error('Błąd podczas zapisywania portfolio');
            }
        })
        .catch(error => {
            showNotification('Błąd podczas zapisywania portfolio', 'danger');
        });
    };
}); 