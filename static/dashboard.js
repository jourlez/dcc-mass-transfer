/* DecentralChain Dashboard JavaScript */

// ==================== State ====================
let isRunning = false;
let logSource = 'stress_test';
let progressChart = null;
let distributionChart = null;

// ==================== Init ====================
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    fetchStatus();
    fetchLogs();
    setInterval(fetchStatus, 2000);
    setInterval(fetchLogs, 3000);
    setInterval(() => {
        const el = document.getElementById('currentTime');
        if (el) el.textContent = new Date().toLocaleTimeString();
    }, 1000);
});

// ==================== API Calls ====================
async function fetchStatus() {
    try {
        const r = await fetch('/api/status');
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const d = await r.json();
        const m = d.metrics || {};
        const w = d.wallets || {};

        setText('totalTx', m.total_tx || 0);
        setText('successTx', m.successful_tx || 0);
        setText('failedTx', m.failed_tx || 0);
        setText('throughput', (m.throughput || 0).toFixed(2));
        setText('retryTx', m.retry_tx || 0);
        setText('elapsedTime', formatTime(m.elapsed_time || 0));

        const total = m.total_tx || 0;
        const succ = m.successful_tx || 0;
        const fail = m.failed_tx || 0;
        const rate = total > 0 ? ((succ/total)*100).toFixed(1) : '0.0';
        const frate = total > 0 ? ((fail/total)*100).toFixed(1) : '0.0';

        setText('successRate', rate + '%');
        setText('failedRate', frate + '%');
        setText('metricTotal', total);
        setText('metricSuccessRate', rate + '%');
        setText('metricThroughput', (m.throughput||0).toFixed(2) + ' tx/sec');
        setText('metricElapsed', (m.elapsed_time||0).toFixed(1) + ' seconds');

        // Errors - always update
        setText('errorTotal', m.error_count || 0);
        setText('errorAsset', m.asset_errors || 0);
        setText('errorBalance', m.balance_errors || 0);
        setText('errorChecksum', m.checksum_errors || 0);
        const errStatus = document.getElementById('errorStatus');
        if (errStatus) {
            const ec = m.error_count || 0;
            errStatus.textContent = ec === 0 ? 'No errors detected' : ec + ' error(s) detected';
            errStatus.style.color = ec === 0 ? '#10b981' : '#ef4444';
        }

        // Wallets
        setText('walletTotal', w.total || 0);
        setText('walletLoaded', w.loaded || 0);
        setText('walletFunded', w.funded || 0);
        setText('walletDepleted', w.depleted || 0);

        // Status badge
        const status = m.current_status || 'idle';
        setText('statusText', status.charAt(0).toUpperCase() + status.slice(1));
        const dot = document.querySelector('.status-dot');
        if (dot) { dot.className = 'status-dot ' + status; }

        if (status === 'completed' || status === 'error' || status === 'stopped') {
            isRunning = false;
            const sb = document.getElementById('startBtn');
            if (sb) { sb.disabled = false; sb.textContent = '▶ Start Test'; }
            const stb = document.getElementById('stopBtn');
            if (stb) stb.disabled = true;
        }

        // Update charts
        if (status === 'running') fetchDetailedMetrics();
        updateDistributionChart(succ, fail, m.retry_tx || 0);
    } catch (e) {
        setText('statusText', 'Disconnected');
        const dot = document.querySelector('.status-dot');
        if (dot) dot.className = 'status-dot error';
    }
}

async function fetchDetailedMetrics() {
    try {
        const r = await fetch('/api/metrics/detailed');
        if (!r.ok) return;
        const d = await r.json();
        if (d.history) updateProgressChart(d.history);
    } catch (e) { /* silent */ }
}

async function fetchLogs() {
    try {
        const r = await fetch('/api/logs/' + logSource);
        if (!r.ok) return;
        const d = await r.json();
        const c = document.getElementById('logsContainer');
        if (c && d.logs && d.logs.trim()) {
            const lines = d.logs.trim().split('\n');
            c.innerHTML = lines.map(l => '<div class="log-line">' + escapeHtml(l) + '</div>').join('');
            c.scrollTop = c.scrollHeight;
        }
    } catch (e) { /* silent */ }
}

// ==================== Controls ====================
async function startTest() {
    const btn = document.getElementById('startBtn');
    btn.disabled = true; btn.textContent = '⏳ Starting...';
    try {
        const r = await fetch('/api/control/start', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
                num_wallets: parseInt(document.getElementById('numWallets').value)||100,
                sends_per_wallet: parseInt(document.getElementById('sendsPerWallet').value)||10,
                workers: parseInt(document.getElementById('workers').value)||20,
                rate_delay: parseFloat(document.getElementById('rateDelay').value)||0.01
            })
        });
        const d = await r.json();
        if (d.success) {
            isRunning = true;
            document.getElementById('stopBtn').disabled = false;
            btn.textContent = '✅ Running';
            addSystemLog('Started PID ' + d.pid + ', ' + d.total_tx + ' TX');
        } else {
            alert('Failed: ' + (d.error||'Unknown'));
            btn.disabled = false; btn.textContent = '▶ Start Test';
        }
    } catch (e) {
        alert('Error: ' + e.message);
        btn.disabled = false; btn.textContent = '▶ Start Test';
    }
}

async function stopTest() {
    try {
        const r = await fetch('/api/control/stop', {method:'POST'});
        const d = await r.json();
        if (d.success) {
            isRunning = false;
            document.getElementById('startBtn').disabled = false;
            document.getElementById('startBtn').textContent = '▶ Start Test';
            document.getElementById('stopBtn').disabled = true;
            addSystemLog('Test stopped');
        }
    } catch (e) { alert('Error: ' + e.message); }
}

function pauseTest() { addSystemLog('Pause not implemented'); }
function setPreset(w,s) {
    document.getElementById('numWallets').value = w;
    document.getElementById('sendsPerWallet').value = s;
    addSystemLog('Preset: ' + w + '×' + s + ' = ' + (w*s) + ' TX');
}

// ==================== Charts ====================
function initCharts() {
    const p = document.getElementById('progressChart');
    if (p) {
        progressChart = new Chart(p.getContext('2d'), {
            type:'line', data:{labels:[],datasets:[
                {label:'TX Count',data:[],borderColor:'#3b82f6',tension:0.3,fill:false},
                {label:'tx/sec',data:[],borderColor:'#10b981',tension:0.3,fill:false,yAxisID:'y1'}
            ]}, options:{responsive:true,scales:{
                y:{beginAtZero:true,ticks:{color:'#9ca3af'}},
                y1:{position:'right',beginAtZero:true,ticks:{color:'#9ca3af'},grid:{drawOnChartArea:false}},
                x:{ticks:{color:'#9ca3af',maxTicksLimit:10}}
            },plugins:{legend:{labels:{color:'#e5e7eb'}}}}
        });
    }
    const d = document.getElementById('distributionChart');
    if (d) {
        distributionChart = new Chart(d.getContext('2d'), {
            type:'doughnut', data:{labels:['Successful','Failed','Retried'],
            datasets:[{data:[0,0,0],backgroundColor:['#10b981','#ef4444','#f59e0b']}]},
            options:{responsive:true,plugins:{legend:{labels:{color:'#e5e7eb'}}}}
        });
    }
}

function updateProgressChart(h) {
    if (!progressChart || !h || !h.timestamps || !h.timestamps.length) return;
    progressChart.data.labels = h.timestamps.map(t => (t.split('T')[1]||'').substring(0,8));
    progressChart.data.datasets[0].data = h.tx_counts || [];
    progressChart.data.datasets[1].data = h.throughputs || [];
    progressChart.update('none');
}

function updateDistributionChart(s,f,r) {
    if (!distributionChart) return;
    distributionChart.data.datasets[0].data = [s,f,r];
    distributionChart.update('none');
}

// ==================== Logs ====================
function switchLogTab(tab) {
    document.querySelectorAll('.logs-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    if (tab==='test') {
        document.getElementById('testLogsTab').classList.add('active');
        document.querySelectorAll('.tab-btn')[0].classList.add('active');
    } else {
        document.getElementById('systemLogsTab').classList.add('active');
        document.querySelectorAll('.tab-btn')[1].classList.add('active');
    }
}
function changeLogSource() {
    logSource = document.getElementById('logScript').value;
    document.getElementById('logsContainer').innerHTML = '<div class="log-line">Loading...</div>';
    fetchLogs();
}
function clearLogs() { document.getElementById('logsContainer').innerHTML = '<div class="log-line" style="color:#9ca3af">Cleared</div>'; }
function clearSystemLogs() { document.getElementById('systemLogsContainer').innerHTML = '<div class="log-line" style="color:#9ca3af">Cleared</div>'; }
function addSystemLog(msg) {
    const c = document.getElementById('systemLogsContainer');
    if (!c) return;
    const l = document.createElement('div');
    l.className = 'log-line';
    l.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
    c.appendChild(l);
    c.scrollTop = c.scrollHeight;
}

// ==================== Quick Actions ====================
function refillTokens() { addSystemLog('Token refill not configured'); }
function refillDCC() { addSystemLog('DCC refill not configured'); }
function exportMetrics() {
    fetch('/api/status').then(r=>r.json()).then(d=>{
        const b = new Blob([JSON.stringify(d,null,2)],{type:'application/json'});
        const a = document.createElement('a');
        a.href = URL.createObjectURL(b);
        a.download = 'metrics_' + Date.now() + '.json';
        a.click();
        addSystemLog('Exported');
    }).catch(e=>addSystemLog('Export failed: '+e.message));
}
function viewWallets() {
    const m = document.getElementById('walletModal');
    if (m) m.style.display = 'flex';
    fetch('/api/wallets/preview?limit=20').then(r=>r.json()).then(d=>{
        const tb = document.getElementById('walletTableBody');
        if (!tb) return;
        tb.innerHTML = (d.wallets||[]).map(w=>
            '<tr><td>'+w.address+'</td><td>••••</td><td>—</td><td>'+w.status+'</td></tr>'
        ).join('') || '<tr><td colspan="4">None</td></tr>';
    }).catch(e=>addSystemLog('Wallet error: '+e.message));
}
function closeModal(id) { const m=document.getElementById(id); if(m) m.style.display='none'; }
