document.addEventListener('DOMContentLoaded', function() {
    const importForm = document.getElementById('importForm');
    const importStatus = document.getElementById('importStatus');
    const importFile = document.getElementById('importFile');
    const importType = document.getElementById('importType');

    const ALLOWED_EXTENSIONS = ['csv', 'xlsx'];
    const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

    function showError(message) {
        importStatus.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill"></i> ${message}
            </div>
        `;
    }

    function showSuccess(message) {
        importStatus.innerHTML = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle-fill"></i> ${message}
            </div>
        `;
    }

    function validateFile(file) {
        // Sprawdź rozszerzenie
        const extension = file.name.split('.').pop().toLowerCase();
        if (!ALLOWED_EXTENSIONS.includes(extension)) {
            throw new Error(`Dozwolone tylko pliki: ${ALLOWED_EXTENSIONS.join(', ')}`);
        }

        // Sprawdź rozmiar
        if (file.size > MAX_FILE_SIZE) {
            throw new Error('Plik jest za duży (max 5MB)');
        }

        return true;
    }

    importForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        importStatus.innerHTML = '';

        try {
            const file = importFile.files[0];
            if (!file) {
                throw new Error('Wybierz plik do importu');
            }

            validateFile(file);

            const formData = new FormData();
            formData.append('file', file);
            formData.append('type', importType.value);

            const response = await fetch('/api/import/data', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            if (response.status === 302 || response.status === 401) {
                window.location.href = '/login';
                return;
            }

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Błąd podczas importu');
            }

            showSuccess(data.message || 'Import zakończony sukcesem');
            importForm.reset();

        } catch (error) {
            showError(error.message);
        }
    });

    // Walidacja w czasie rzeczywistym
    importFile.addEventListener('change', function() {
        try {
            const file = this.files[0];
            if (file) {
                validateFile(file);
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        } catch (error) {
            this.classList.remove('is-valid');
            this.classList.add('is-invalid');
            showError(error.message);
        }
    });
}); 