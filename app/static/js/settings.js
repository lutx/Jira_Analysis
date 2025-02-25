document.addEventListener('DOMContentLoaded', function() {
    const settingsForm = document.querySelector('#settingsForm');
    if (settingsForm) {
        settingsForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            try {
                const formData = new FormData(this);
                const response = await fetch(this.action, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                    },
                    body: formData
                });
                
                if (response.ok) {
                    const toast = new bootstrap.Toast(document.querySelector('.toast'));
                    toast.show();
                } else {
                    const data = await response.json();
                    alert(data.error || 'Error saving settings');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error saving settings');
            }
        });
    }
}); 