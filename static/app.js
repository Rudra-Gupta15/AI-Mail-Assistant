document.addEventListener('DOMContentLoaded', () => {
    fetchStatus();
    
    // Gmail Sync
    const syncBtn = document.getElementById('btn-sync-gmail');
    const syncSpinner = document.getElementById('sync-spinner');
    const syncText = document.getElementById('sync-text');
    const syncResults = document.getElementById('sync-results');

    syncBtn.addEventListener('click', async () => {
        syncBtn.disabled = true;
        syncSpinner.classList.remove('hidden');
        syncText.textContent = 'Syncing...';
        syncResults.innerHTML = '<p>Searching for unread emails...</p>';

        try {
            const res = await fetch('/api/v1/gmail/sync');
            const data = await res.json();
            
            if (data.error) {
                syncResults.innerHTML = `<p style="color: #ef4444;">Error: ${data.error}</p>`;
            } else {
                syncResults.innerHTML = `<p>Found ${data.synced} unread emails.</p>`;
                if (data.actions && data.actions.length > 0) {
                    const list = data.actions.map(a => `<li>${a.subject} -> <b>${a.status}</b></li>`).join('');
                    syncResults.innerHTML += `<ul style="margin-top: 10px; padding-left: 20px;">${list}</ul>`;
                }
            }
        } catch (err) {
            syncResults.innerHTML = `<p style="color: #ef4444;">Failed to connect to server.</p>`;
        } finally {
            syncBtn.disabled = false;
            syncSpinner.classList.add('hidden');
            syncText.textContent = 'Sync Now';
        }
    });

    // Manual AI Draft
    const draftBtn = document.getElementById('btn-test-ai');
    const draftOutput = document.getElementById('ai-draft-output');
    const draftText = document.getElementById('draft-text');

    draftBtn.addEventListener('click', async () => {
        const sender = document.getElementById('test-sender').value;
        const subject = document.getElementById('test-subject').value;
        const body = document.getElementById('test-body').value;

        if (!sender || !subject || !body) {
            alert('Please fill in all fields.');
            return;
        }

        draftBtn.disabled = true;
        draftBtn.textContent = 'Processing...';

        try {
            const res = await fetch('/api/v1/process-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sender, subject, body, context: 'manual_gui' })
            });
            const data = await res.json();
            
            draftOutput.classList.remove('hidden');
            draftText.textContent = data.ai_response;
        } catch (err) {
            alert('Draft generation failed.');
        } finally {
            draftBtn.disabled = false;
            draftBtn.textContent = 'Generate Draft';
        }
    });
});

async function fetchStatus() {
    try {
        const res = await fetch('/api/v1/health');
        const data = await res.json();
        
        const engineDot = document.getElementById('engine-dot');
        const engineStatus = document.getElementById('engine-status');
        const modelName = document.getElementById('model-name');
        const availableTags = document.getElementById('available-models');

        if (data.status === 'healthy') {
            engineDot.className = 'status-dot green';
            engineStatus.textContent = 'Active';
            modelName.textContent = data.model;
            
            if (data.available_models) {
                availableTags.innerHTML = data.available_models
                    .map(m => `<span class="tag">${m}</span>`)
                    .join('');
            }
        } else {
            engineDot.className = 'status-dot red';
            engineStatus.textContent = 'Offline';
            modelName.textContent = 'Ollama Disconnected';
        }
    } catch (err) {
        console.error('Failed to fetch status');
    }
}
