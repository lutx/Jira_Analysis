console.log('Debug: JIRA sync script loading...');

// Helper functions
function updateSyncStatus(message, isLoading = false, progress = null, details = null) {
    console.log('Debug: Updating sync status:', { message, isLoading, progress, details });
    const statusDiv = document.getElementById('sync-status');
    const spinner = document.getElementById('sync-spinner');
    const messageSpan = document.getElementById('sync-message');
    const progressBar = document.getElementById('sync-progress');
    const progressBarInner = document.getElementById('sync-progress-bar');
    const detailsDiv = document.getElementById('sync-details');
    
    if (!statusDiv || !spinner || !messageSpan || !progressBar || !progressBarInner || !detailsDiv) {
        console.error('Debug: Required elements not found:', {
            statusDiv: !!statusDiv,
            spinner: !!spinner,
            messageSpan: !!messageSpan,
            progressBar: !!progressBar,
            progressBarInner: !!progressBarInner,
            detailsDiv: !!detailsDiv
        });
        return;
    }
    
    statusDiv.classList.remove('d-none', 'alert-info', 'alert-success', 'alert-danger');
    statusDiv.classList.add('alert-info');
    
    if (isLoading) {
        spinner.classList.remove('d-none');
        progressBar.classList.remove('d-none');
        
        if (progress !== null) {
            progressBarInner.style.width = `${progress}%`;
            progressBarInner.textContent = `${progress}%`;
        }
    } else {
        spinner.classList.add('d-none');
        progressBar.classList.add('d-none');
        statusDiv.classList.add(message.includes('Error') ? 'alert-danger' : 'alert-success');
    }
    
    messageSpan.textContent = message;
    
    if (details) {
        detailsDiv.textContent = details;
        detailsDiv.classList.remove('d-none');
    } else {
        detailsDiv.classList.add('d-none');
    }
}

function simulateProgress(actionName) {
    console.log('Debug: Starting progress simulation for:', actionName);
    let progress = 0;
    return setInterval(() => {
        progress += Math.random() * 15;
        if (progress <= 90) {
            updateSyncStatus(
                `${actionName} in progress...`, 
                true, 
                Math.min(Math.round(progress), 90),
                `Processing data...`
            );
        }
    }, 500);
}

window.performSync = async function(endpoint, button) {
    console.log('Debug: Performing sync:', { endpoint, button: button.id });
    
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (!csrfToken) {
        console.error('Debug: CSRF token not found');
        alert('CSRF token not found. Please refresh the page.');
        return;
    }
    console.log('Debug: CSRF token found');

    // Show initial status
    updateSyncStatus('Starting synchronization...', true, 0);

    // Disable all sync buttons
    const allButtons = document.querySelectorAll('[id^="sync-"]');
    allButtons.forEach(btn => {
        btn.disabled = true;
        console.log('Debug: Disabled button:', btn.id);
    });

    // Show loading state on clicked button
    const originalText = button.innerHTML;
    button.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${button.textContent.trim()}`;
    console.log('Debug: Updated button text');

    // Show progress
    const progressInterval = simulateProgress(button.textContent.trim());

    try {
        console.log('Debug: Making fetch request to:', endpoint);
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            credentials: 'same-origin'
        });

        console.log('Debug: Response received:', response.status);
        
        let data;
        try {
            const text = await response.text();
            console.log('Debug: Raw response:', text);
            data = text ? JSON.parse(text) : {};
        } catch (e) {
            console.error('Debug: Error parsing response:', e);
            throw new Error('Invalid server response');
        }

        clearInterval(progressInterval);

        if (data.status === 'success') {
            console.log('Debug: Sync successful');
            updateSyncStatus(
                `Sync completed successfully!`,
                false,
                100,
                JSON.stringify(data.stats || data.results, null, 2)
            );
            setTimeout(() => window.location.reload(), 2000);
        } else {
            throw new Error(data.message || 'Unknown error occurred');
        }
    } catch (error) {
        console.error('Debug: Sync error:', error);
        clearInterval(progressInterval);
        updateSyncStatus(
            `Error during sync: ${error.message}`,
            false,
            null,
            error.stack
        );
    } finally {
        // Re-enable all buttons
        allButtons.forEach(btn => {
            btn.disabled = false;
            if (btn === button) {
                btn.innerHTML = originalText;
            }
            console.log('Debug: Re-enabled button:', btn.id);
        });
    }
}

window.testJiraConnection = async function() {
    console.log('Debug: Testing JIRA connection');
    const url = document.getElementById('url').value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (!url || !username) {
        console.warn('Debug: Missing required fields');
        alert('Please fill in the URL and username fields');
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (!csrfToken) {
        console.error('Debug: CSRF token not found');
        alert('CSRF token not found. Please refresh the page.');
        return;
    }

    const button = document.getElementById('test-connection');
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Testing...';

    try {
        console.log('Debug: Making test connection request');
        const response = await fetch('/admin/jira/test-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            body: JSON.stringify({ url, username, password })
        });

        const data = await response.json();
        console.log('Debug: Test connection response:', data);
        alert(data.message);
    } catch (error) {
        console.error('Debug: Error testing connection:', error);
        alert('Error testing connection: ' + error.message);
    } finally {
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

console.log('Debug: JIRA sync script loaded successfully'); 