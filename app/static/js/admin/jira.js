function testConnection() {
    const btn = document.querySelector('#test-connection');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testowanie...';
    
    fetch('/panel-admina/jira/test-connection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            Swal.fire('Sukces', 'Połączenie z JIRA działa prawidłowo', 'success');
        } else {
            Swal.fire('Błąd', data.message || 'Błąd połączenia z JIRA', 'error');
        }
    })
    .catch(error => {
        Swal.fire('Błąd', 'Wystąpił błąd podczas testowania połączenia', 'error');
        console.error('Error:', error);
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = originalText;
    });
} 