document.addEventListener('DOMContentLoaded', () => {
    // Initialize system status
    updateSystemStatus();
    setInterval(updateSystemStatus, 10000);

    // Dom Elements
    const syncBtn = document.getElementById('btn-sync-gmail');
    const syncLoader = document.getElementById('sync-loader');
    const lastSyncTime = document.getElementById('last-sync-time');
    const syncSummary = document.getElementById('sync-summary');

    const generateBtn = document.getElementById('btn-generate');
    const previewPanel = document.getElementById('preview-panel');
    const draftContent = document.getElementById('draft-text-content');
    const tagType = document.getElementById('tag-type');

    // State for pending approvals and human reviews
    const pendingActions = new Map(); // sender -> { classification, sender_str }
    const pendingList = document.getElementById('pending-list');
    const refreshApprovalsBtn = document.getElementById('btn-refresh-approvals');

    // Reusable Sync Function
    async function syncGmail(showLoading = true) {
        if (showLoading) {
            setLoading(syncBtn, syncLoader, true);
            if (refreshApprovalsBtn) refreshApprovalsBtn.querySelector('i').classList.add('refresh-spinning');
        }
        
        syncSummary.innerHTML = '<span class="status-working">Searching for new messages...</span>';

        try {
            const response = await fetch('/api/v1/gmail/sync');
            const data = await response.json();

            if (data.error) {
                syncSummary.innerHTML = `<span class="text-danger">${data.error}</span>`;
            } else {
                lastSyncTime.textContent = new Date().toLocaleTimeString();
                syncSummary.innerHTML = `<span>Successfully processed <b>${data.synced}</b> emails.</span>`;
                
                // Track pending approvals and human reviews
                if (data.actions) {
                    let hasNew = false;
                    data.actions.forEach(action => {
                        // We show both PENDING (new sender) and HUMAN (whitelisted but complex)
                        if ((action.classification === 'PENDING' || action.classification === 'HUMAN') && action.sender) {
                            if (!pendingActions.has(action.sender)) {
                                pendingActions.set(action.sender, {
                                    id: action.id,
                                    threadId: action.threadId,
                                    classification: action.classification,
                                    sender_str: action.sender,
                                    timestamp: action.timestamp
                                });
                                hasNew = true;
                            }
                        }
                    });
                    // Always try to update if we have items, to ensure state is clear
                    if (hasNew || pendingActions.size > 0) updatePendingUI();
                }
            }
        } catch (error) {
            syncSummary.innerHTML = '<span class="text-danger">Connection failed. Is the server running?</span>';
        } finally {
            if (showLoading) {
                setLoading(syncBtn, syncLoader, false);
                if (refreshApprovalsBtn) refreshApprovalsBtn.querySelector('i').classList.remove('refresh-spinning');
            }
        }
    }

    // Gmail Sync Handlers
    syncBtn.addEventListener('click', () => syncGmail(true));
    if (refreshApprovalsBtn) {
        refreshApprovalsBtn.addEventListener('click', () => syncGmail(true));
    }

    // Auto-refresh every 60 seconds
    setInterval(() => syncGmail(false), 60000);

    // Initial sync
    setTimeout(() => syncGmail(false), 2000);

    function updatePendingUI() {
        if (!pendingList) return;
        
        if (pendingActions.size === 0) {
            pendingList.innerHTML = '<li class="empty-state">No items requiring attention.</li>';
            return;
        }

        pendingList.innerHTML = '';
        pendingActions.forEach((action, sender_str) => {
            const li = document.createElement('li');
            li.className = 'approval-item';
            if (action.classification === 'HUMAN') li.classList.add('review-required');
            
            // Safer extraction
            const emailMatch = sender_str.match(/<(.+)>/);
            const email = emailMatch ? emailMatch[1] : sender_str;
            const name = sender_str.split('<')[0].trim() || email;

            const isHumanReview = action.classification === 'HUMAN';
            
            // Smarter timestamp: Show date if not today
            let timeStr = '';
            if (action.timestamp) {
                const date = new Date(action.timestamp * 1000);
                const today = new Date();
                const isToday = date.getDate() === today.getDate() && 
                                date.getMonth() === today.getMonth() && 
                                date.getFullYear() === today.getFullYear();
                
                const timeOptions = { hour: '2-digit', minute: '2-digit' };
                if (isToday) {
                    timeStr = date.toLocaleTimeString([], timeOptions);
                } else {
                    const dateOptions = { month: 'short', day: 'numeric' };
                    timeStr = `${date.toLocaleDateString([], dateOptions)}, ${date.toLocaleTimeString([], timeOptions)}`;
                }
            }

            li.innerHTML = `
                <div class="approval-info">
                    <div class="sender-top">
                        <span class="approval-email"></span>
                        <span class="classification-badge ${action.classification.toLowerCase()}">${action.classification}</span>
                        <span class="arrival-time">${timeStr}</span>
                    </div>
                    <small></small>
                </div>
                <div class="approval-actions">
                    ${!isHumanReview ? `
                        <button class="single-allow-btn" title="Allow for this session only">
                            <i class="fas fa-clock"></i> Single
                        </button>
                        <button class="multi-allow-btn" title="Permanently whitelist">
                            <i class="fas fa-check-double"></i> Multiple
                        </button>
                    ` : `
                        <button class="process-btn" title="Process with AI now">
                            <i class="fas fa-robot"></i> Process
                        </button>
                    `}
                </div>
            `;
            
            li.querySelector('.approval-email').textContent = name;
            li.querySelector('small').textContent = email;
            
            if (!isHumanReview) {
                li.querySelector('.single-allow-btn').onclick = () => window.approveOnce(email, sender_str, li.querySelector('.single-allow-btn'));
                li.querySelector('.multi-allow-btn').onclick = () => window.allowSender(email, sender_str, li.querySelector('.multi-allow-btn'));
            } else {
                li.querySelector('.process-btn').onclick = () => window.processSingle(action.id, action.threadId, sender_str, li.querySelector('.process-btn'));
            }
            
            pendingList.appendChild(li);
        });
    }

    // --- Global Handlers for Approval ---
    window.processSingle = async function(id, threadId, sender_str, btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        try {
            const response = await fetch('/api/v1/gmail/process-single', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, threadId })
            });
            
            const data = await response.json();
            if (response.ok && data.status === 'success') {
                const item = btn.closest('.approval-item');
                item.style.opacity = '0.5';
                btn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => {
                    item.remove();
                    pendingActions.delete(sender_str);
                    if (pendingActions.size === 0) updatePendingUI();
                }, 1000);
            } else {
                alert(data.message || 'Failed to process email.');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-robot"></i> Process';
            }
        } catch (e) {
            alert('Error communicating with server.');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-robot"></i> Process';
        }
    };

    window.approveOnce = async function(email, sender_str, btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        try {
            const response = await fetch('/api/v1/approve-once', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            
            if (response.ok) {
                const item = btn.closest('.approval-item');
                item.style.opacity = '0.5';
                btn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => {
                    item.remove();
                    pendingActions.delete(sender_str);
                    if (pendingActions.size === 0) updatePendingUI();
                }, 1000);
            }
        } catch (e) {
            alert('Failed to approve once.');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-clock"></i> Single';
        }
    };

    window.allowSender = async function(email, sender_str, btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        try {
            const response = await fetch('/api/v1/allow-sender', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            
            if (response.ok) {
                const item = btn.closest('.approval-item');
                item.style.opacity = '0.5';
                btn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => {
                    item.remove();
                    pendingActions.delete(sender_str);
                    if (pendingActions.size === 0) updatePendingUI();
                }, 1000);
            }
        } catch (e) {
            alert('Failed to whitelist sender.');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check-double"></i> Multiple';
        }
    };

    // --- AI Email Composer Logic ---
    const composerRecipient = document.getElementById('composer-recipient');
    const composerSubject = document.getElementById('composer-subject');
    const composerPrompt = document.getElementById('composer-prompt');
    const createDraftBtn = document.getElementById('btn-create-draft');
    const rewriteBtn = document.getElementById('btn-composer-rewrite');
    const sendBtn = document.getElementById('btn-composer-send');
    const composerResult = document.getElementById('composer-result');
    const composerOutput = document.getElementById('composer-output');

    async function generateComposerDraft() {
        const recipient = composerRecipient.value;
        const subject = composerSubject.value;
        const prompt = composerPrompt.value;

        if (!recipient || !subject || !prompt) {
            alert('Please provide Recipient, Subject, and Prompt.');
            return;
        }

        createDraftBtn.disabled = true;
        rewriteBtn.disabled = true;
        const originalText = createDraftBtn.innerHTML;
        createDraftBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

        try {
            const response = await fetch('/api/v1/gmail/create-draft', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ recipient, subject, prompt })
            });
            const data = await response.json();

            if (data.status === 'success') {
                composerOutput.value = data.draft;
                composerResult.classList.remove('hidden');
                composerResult.scrollIntoView({ behavior: 'smooth', block: 'end' });
            } else {
                alert(data.error || 'Failed to generate draft.');
            }
        } catch (error) {
            alert('Consultation with AI failed. Check Ollama status.');
        } finally {
            createDraftBtn.disabled = false;
            rewriteBtn.disabled = false;
            createDraftBtn.innerHTML = originalText;
        }
    }

    createDraftBtn.addEventListener('click', generateComposerDraft);
    rewriteBtn.addEventListener('click', generateComposerDraft);

    sendBtn.addEventListener('click', async () => {
        const recipient = composerRecipient.value;
        const subject = composerSubject.value;
        const body = composerOutput.value;

        if (!recipient || !subject || !body) {
            alert('Recipient, Subject, and Content are required to send.');
            return;
        }

        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';

        try {
            const response = await fetch('/api/v1/gmail/send-new', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ recipient, subject, body })
            });
            const data = await response.json();

            if (data.status === 'success') {
                alert('Email sent successfully!');
                // Reset form
                composerRecipient.value = '';
                composerSubject.value = '';
                composerPrompt.value = '';
                composerResult.classList.add('hidden');
            } else {
                alert('Failed to send email.');
            }
        } catch (error) {
            alert('Error sending email.');
        } finally {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i><span>Send Now</span>';
        }
    });

    // Handle old references if they still exist in the script but not in DOM
    const oldGenerateBtn = document.getElementById('btn-generate');
    if (oldGenerateBtn) {
        oldGenerateBtn.addEventListener('click', () => alert('This feature is now the AI Email Creator.'));
    }

    // --- User Identity Logic ---
    const userNameInput = document.getElementById('user-name');
    const userEmailInput = document.getElementById('user-email');
    const saveInfoBtn = document.getElementById('btn-save-info');
    const displayDate = document.getElementById('current-display-date');

    // Display current date
    if (displayDate) {
        displayDate.textContent = new Date().toLocaleDateString('en-US', { 
            month: 'long', day: 'numeric', year: 'numeric' 
        });
    }

    // Load user info
    async function loadUserInfo() {
        try {
            const response = await fetch('/api/v1/user-info');
            const data = await response.json();
            if (data.name) userNameInput.value = data.name;
            if (data.email) userEmailInput.value = data.email;
        } catch (e) {
            console.error('Failed to load user info');
        }
    }

    saveInfoBtn.addEventListener('click', async () => {
        const name = userNameInput.value;
        const email = userEmailInput.value;

        if (!name || !email) {
            alert('Name and Email are required.');
            return;
        }

        saveInfoBtn.disabled = true;
        saveInfoBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

        try {
            const response = await fetch('/api/v1/user-info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email })
            });

            if (response.ok) {
                saveInfoBtn.innerHTML = '<i class="fas fa-check"></i> Saved';
                setTimeout(() => {
                    saveInfoBtn.innerHTML = '<i class="fas fa-save"></i> <span>Save Identity</span>';
                    saveInfoBtn.disabled = false;
                }, 2000);
            }
        } catch (error) {
            alert('Failed to save identity.');
            saveInfoBtn.disabled = false;
            saveInfoBtn.innerHTML = '<i class="fas fa-save"></i> <span>Save Identity</span>';
        }
    });

    // Helper Modal Handlers
    const helperNav = document.getElementById('nav-helper');
    const helperModal = document.getElementById('helper-modal');
    const closeModal = document.querySelector('.close-modal');

    if (helperNav && helperModal) {
        helperNav.addEventListener('click', (e) => {
            e.preventDefault();
            helperModal.classList.remove('hidden');
        });

        closeModal.addEventListener('click', () => {
            helperModal.classList.add('hidden');
        });

        window.addEventListener('click', (e) => {
            if (e.target === helperModal) {
                helperModal.classList.add('hidden');
            }
        });
    }

    // Active Nav Handler
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            if (item.id === 'nav-helper') return; 
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });

    loadUserInfo();
});

async function updateSystemStatus() {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const modelDisplay = document.getElementById('model-display');
    const waStatus = document.getElementById('wa-status');

    try {
        const response = await fetch('/api/v1/health');
        const data = await response.json();

        if (data.status === 'healthy') {
            statusDot.className = 'dot online pulsing';
            statusText.textContent = 'Ollama: Online';
            modelDisplay.textContent = data.model;
        } else {
            statusDot.className = 'dot offline';
            statusText.textContent = 'Ollama: Offline';
        }

        // WhatsApp Status
        if (data.whatsapp_connected) {
            waStatus.className = 'status-badge success-bg';
            waStatus.querySelector('.badge-dot').style.background = '#16a34a';
            waStatus.querySelector('.badge-text').textContent = 'Live';
        } else {
            waStatus.className = 'status-badge';
            waStatus.querySelector('.badge-dot').style.background = '#94a3b8';
            waStatus.querySelector('.badge-text').textContent = 'Inactive';
        }

        // Gmail Status
        const gmailBadge = document.querySelector('.icon-circle.gmail-bg');
        if (data.gmail_connected) {
            gmailBadge.style.boxShadow = '0 0 15px rgba(220, 38, 38, 0.2)';
        }

    } catch (e) {
        statusDot.className = 'dot offline';
        statusText.textContent = 'Server: Down';
    }
}

function setLoading(btn, loader, isLoading) {
    if (isLoading) {
        btn.disabled = true;
        loader.classList.remove('hidden');
        btn.querySelector('span').textContent = 'Syncing...';
    } else {
        btn.disabled = false;
        loader.classList.add('hidden');
        btn.querySelector('span').textContent = 'Process Unread';
    }
}

