const stateElements = {
    taskId: document.getElementById('task-id'),
    sessionId: document.getElementById('session-id'),
    custName: document.getElementById('cust-name'),
    custTier: document.getElementById('cust-tier'),
    ticketPriority: document.getElementById('ticket-priority'),
    ticketSentiment: document.getElementById('ticket-sentiment'),
    latestMsg: document.getElementById('latest-msg'),
    actionFeed: document.getElementById('action-feed'),
    toolsLog: document.getElementById('tools-log'),
    avgReward: document.getElementById('avg-reward'),
    totalEpisodes: document.getElementById('total-episodes'),
    difficultyText: document.getElementById('difficulty-text'),
    progressBar: document.getElementById('progress-bar'),
    progressPercent: document.getElementById('progress-percent'),
    resetBtn: document.getElementById('reset-btn'),
    summaryOverlay: document.getElementById('summary-overlay'),
    summaryTaskId: document.getElementById('summary-task-id'),
    summaryScore: document.getElementById('summary-score'),
    summarySteps: document.getElementById('summary-steps'),
    summaryCloseBtn: document.getElementById('summary-close-btn'),
    runDemoBtn: document.getElementById('run-demo-btn'),
    demoStatus: document.getElementById('demo-status'),
    demoMsg: document.getElementById('demo-msg')
};

let knownFeedIds = new Set();
let currentEpisodeId = null;
let isUpdating = false;

// Create an SVG icon based on action type
function getActionIcon(type) {
    const icons = {
        lookup: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>`,
        reply: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 1 1-7.6-14.7 8.38 8.38 0 0 1 3.8.9"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`,
        escalate: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>`,
        close: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="9" x2="15" y2="15"></line><line x1="15" y1="9" x2="9" y2="15"></line></svg>`,
        refund: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>`,
        update_ticket: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>`,
        internal_note: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>`
    };
    return icons[type.toLowerCase()] || icons.reply;
}

function getScoreTag(score) {
    if (score >= 0.80) return { class: 'tag-success', label: 'OPTIMAL' };
    if (score >= 0.50) return { class: 'tag-warning', label: 'FAIR' };
    return { class: 'tag-danger', label: 'POOR' };
}

// Simple syntax highlighting for JSON-like strings
function formatJson(json) {
    if (typeof json !== 'string') {
        json = JSON.stringify(json, null, 2);
    }
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        let cls = 'number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'key';
            } else {
                cls = 'string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'boolean';
        } else if (/null/.test(match)) {
            cls = 'null';
        }
        return `<span class="json-${cls}">${match}</span>`;
    });
}

async function fetchCurriculum() {
    try {
        const res = await fetch('/curriculum');
        if (!res.ok) return;
        const data = await res.json();
        const stats = data.curriculum || {};
        
        stateElements.avgReward.innerText = (stats.avg_reward || 0).toFixed(4);
        stateElements.totalEpisodes.innerText = (stats.episode_count || 0).toLocaleString();
        
        let progress = ((stats.avg_reward || 0) / 1.0) * 100; // Normalized to 1.0
        progress = Math.min(Math.max(progress, 0), 100);
        
        stateElements.progressBar.style.width = `${progress}%`;
        stateElements.progressPercent.innerText = `${Math.round(progress)}%`;
    } catch (err) {
        console.error('Failed to fetch curriculum:', err);
    }
}

async function updateDashboard() {
    if (isUpdating) return;
    isUpdating = true;
    
    try {
        const res = await fetch('/state');
        if (!res.ok) throw new Error('API Error');
        const data = await res.json();
        
        if (!data.initialized) {
            stateElements.latestMsg.innerText = 'Environment Standby - Press "Run AI Agent Demo" to begin.';
            stateElements.taskId.innerText = 'Awaiting Session';
            return;
        }

        const state = data.state;

        // Auto-reset UI if episode ID changed (new session started by inference.py)
        if (state.episode_id && state.episode_id !== currentEpisodeId) {
            currentEpisodeId = state.episode_id;
            knownFeedIds.clear();
            stateElements.actionFeed.innerHTML = '';
            stateElements.summaryOverlay.classList.add('hidden');
            stateElements.latestMsg.innerText = 'Initializing...';
        }
        
        // Update header details
        stateElements.taskId.innerText = (state.task_id || 'Waiting...').replace(/_/g, ' ');
        stateElements.sessionId.innerText = state.episode_id || '---';
        stateElements.difficultyText.innerText = (state.difficulty || 'easy').toUpperCase();
        
        // Update Observation Matrix
        const ticket = state.ticket || {};
        const customer = state.customer || {};
        
        stateElements.custName.innerText = customer.name || 'Anonymous';
        stateElements.custTier.innerText = (customer.account_tier || 'basic').toUpperCase();
        stateElements.custTier.className = `tag tag-info tier-${customer.account_tier}`;
        
        stateElements.ticketPriority.innerText = (ticket.priority || 'NORMAL').toUpperCase();
        stateElements.ticketSentiment.innerText = (ticket.sentiment || 'NEUTRAL').toUpperCase();
        
        const history = state.conversation || [];
        if (history.length > 0) {
            const lastMsg = history[history.length - 1];
            stateElements.latestMsg.innerText = lastMsg.content;
            stateElements.latestMsg.style.borderColor = 
                lastMsg.role === 'agent' ? 'var(--accent-primary)' : 'var(--border-color)';
        }

        // Process Action Feed smoothly
        const actions = state.actions_taken || [];
        const scores = state.step_score_history || [];
        let addedNew = false;
        
        for (let i = 0; i < actions.length; i++) {
            const action = actions[i];
            const score = scores[i] || 0;
            const itemId = `step-${action.type}-${i}-${state.episode_id}`;
            
            if (!knownFeedIds.has(itemId)) {
                addedNew = true;
                const div = document.createElement('div');
                div.className = 'feed-item';
                
                const scoreInfo = getScoreTag(score);
                const icon = getActionIcon(action.type);
                
                let detailText = action.message || '';
                if (action.type === 'lookup' && action.tool_name) {
                    detailText = `Invoked <strong>${action.tool_name}</strong>`;
                } else if (action.type === 'refund') {
                    detailText = `Processed refund for order <strong>${action.tool_input?.order_id || '---'}</strong>`;
                }

                div.innerHTML = `
                    <div class="feed-header">
                        <span class="feed-title">
                            <span class="feed-icon">${icon}</span>
                            ${action.type.replace(/_/g, ' ')}
                        </span>
                        <span class="tag ${scoreInfo.class}">${score.toFixed(2)} PTS</span>
                    </div>
                    <div class="feed-content">
                        ${detailText}
                    </div>
                `;
                
                stateElements.actionFeed.prepend(div);
                knownFeedIds.add(itemId);
                await new Promise(r => setTimeout(r, 100));
            }
        }
        
        if (addedNew) {
            stateElements.actionFeed.scrollTop = 0;
        }

        // Update Tools Terminal
        const systemMsgs = history.filter(m => m.role === 'system' && m.content.includes('[Tool:'));
        if (systemMsgs.length > 0) {
            const lastToolMsg = systemMsgs[systemMsgs.length - 1].content;
            stateElements.toolsLog.innerHTML = formatJson(lastToolMsg);
        }

        // Check if episode is done to show/hide summary
        if (state.done) {
            showSummary(state);
        } else {
            stateElements.summaryOverlay.classList.add('hidden');
        }

        await fetchCurriculum();

    } catch (err) {
        console.error('Update failed:', err);
    } finally {
        isUpdating = false;
    }
}

function showSummary(state) {
    stateElements.summaryTaskId.innerText = `Task: ${state.task_id.replace(/_/g, ' ')}`;
    stateElements.summaryScore.innerText = state.total_reward.toFixed(2);
    stateElements.summarySteps.innerText = state.step_count;
    stateElements.summaryOverlay.classList.remove('hidden');
}

stateElements.summaryCloseBtn.onclick = () => {
    stateElements.summaryOverlay.classList.add('hidden');
    stateElements.resetBtn.click();
};

stateElements.resetBtn.onclick = async () => {
    stateElements.resetBtn.disabled = true;
    stateElements.resetBtn.innerText = 'Resetting...';
    try {
        await fetch('/reset', { 
            method: 'POST', 
            body: JSON.stringify({}), 
            headers: {'Content-Type': 'application/json'} 
        });
        knownFeedIds.clear();
        stateElements.actionFeed.innerHTML = '';
        stateElements.latestMsg.innerText = 'Waiting for input...';
        stateElements.toolsLog.innerText = '{"status": "awaiting_tools"}';
        stateElements.summaryOverlay.classList.add('hidden');
        setTimeout(() => location.reload(), 500);
    } catch(e) {
        console.error(e);
    } finally {
        stateElements.resetBtn.disabled = false;
        stateElements.resetBtn.innerText = 'Force Reload';
    }
};

stateElements.runDemoBtn.onclick = async () => {
    stateElements.runDemoBtn.disabled = true;
    stateElements.demoStatus.innerText = 'STARTING...';
    try {
        const res = await fetch('/run-demo', { method: 'POST' });
        const data = await res.json();
        stateElements.demoMsg.innerText = data.message;
    } catch (err) {
        stateElements.demoMsg.innerText = 'Failed to launch agent.';
    } finally {
        setTimeout(() => {
            stateElements.runDemoBtn.disabled = false;
        }, 5000);
    }
};

async function checkDemoStatus() {
    try {
        const res = await fetch('/demo-status');
        if (!res.ok) return;
        const data = await res.json();
        
        stateElements.demoStatus.innerText = data.status.toUpperCase();
        stateElements.demoStatus.className = `tag tag-${data.status === 'running' ? 'success' : 'info'}`;
        
        if (data.status === 'running') {
            stateElements.runDemoBtn.classList.add('hidden');
        } else {
            stateElements.runDemoBtn.classList.remove('hidden');
        }
    } catch (err) {
        console.error('Status check failed:', err);
    }
}

// Start Pipeline
setInterval(updateDashboard, 1500);
setInterval(checkDemoStatus, 3000);
setInterval(fetchAgentLogs, 2000);
updateDashboard();
checkDemoStatus();
fetchAgentLogs();

async function fetchAgentLogs() {
    const logsEl = document.getElementById('agent-logs');
    if (!logsEl) return;
    
    try {
        const res = await fetch('/agent-logs');
        if (!res.ok) return;
        const data = await res.json();
        
        // Only update if there's new content to avoid unnecessary DOM work
        if (data.logs && data.logs !== logsEl.innerText) {
            logsEl.innerText = data.logs;
            // Smoothly scroll to the bottom to see latest logs
            logsEl.scrollTop = logsEl.scrollHeight;
        }
    } catch (err) {
        console.error('Failed to fetch logs:', err);
    }
}
