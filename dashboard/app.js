/**
 * DisputeForge — Dashboard Application Logic
 *
 * Handles batch analysis, result rendering, filtering,
 * and detail modals for the premium dashboard.
 */

let allResults = [];
let batchMetrics = null;

// ── Init ─────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
});

async function checkHealth() {
    const badge = document.getElementById('modelStatus');
    try {
        const res = await fetch('/api/health');
        const data = await res.json();
        if (data.model_loaded) {
            badge.className = 'status-badge ready';
            badge.innerHTML = '<span class="status-dot"></span><span>Model Ready</span>';
        } else {
            badge.className = 'status-badge';
            badge.innerHTML = '<span class="status-dot"></span><span>Model Not Trained</span>';
        }
    } catch {
        badge.className = 'status-badge error';
        badge.innerHTML = '<span class="status-dot"></span><span>API Offline</span>';
    }
}

// ── Batch Analysis ───────────────────────────────────────────────────────

async function runBatchAnalysis() {
    const btn = document.getElementById('runAnalysisBtn');
    const loading = document.getElementById('loadingOverlay');

    btn.disabled = true;
    loading.style.display = 'flex';

    try {
        const res = await fetch('/api/analyze-batch', { method: 'POST' });
        const data = await res.json();

        allResults = data.results || [];
        batchMetrics = data.batch_metrics || {};

        renderMetrics(batchMetrics);
        renderResults(allResults);

        document.getElementById('detailSection').style.display = 'grid';
        document.getElementById('resultsPanel').style.display = 'block';
        document.getElementById('fpBanner').style.display = 'flex';

    } catch (err) {
        console.error('Analysis failed:', err);
        alert('Analysis failed. Is the server running?\n\nRun: python3 -m uvicorn app.main:app --reload');
    } finally {
        btn.disabled = false;
        loading.style.display = 'none';
    }
}

// ── Render Metrics ───────────────────────────────────────────────────────

function renderMetrics(m) {
    document.getElementById('metricTotal').textContent = m.total_transactions || 0;

    const flagged = m.flagged_high_risk || 0;
    document.getElementById('metricFlagged').textContent = flagged;
    document.getElementById('metricFlaggedPct').textContent =
        m.total_transactions ? `${((flagged / m.total_transactions) * 100).toFixed(1)}% of batch` : '—';

    document.getElementById('metricDeflections').textContent = m.deflections_generated || 0;

    const precision = m.precision || 0;
    document.getElementById('metricPrecision').textContent = `${(precision * 100).toFixed(1)}%`;

    const recall = m.recall || 0;
    document.getElementById('metricRecall').textContent = `${(recall * 100).toFixed(1)}%`;

    const f1 = m.f1_score || 0;
    document.getElementById('metricF1').textContent = f1.toFixed(3);

    // Confusion matrix
    document.getElementById('cmTN').textContent = m.true_negatives || 0;
    document.getElementById('cmFP').textContent = m.false_alarms || 0;
    document.getElementById('cmFN').textContent = m.missed_disputes || 0;
    document.getElementById('cmTP').textContent = m.correctly_flagged || 0;

    // FP cost
    document.getElementById('fpCostText').textContent = m.false_positive_cost || '—';
}

// ── Render Results Table ─────────────────────────────────────────────────

function renderResults(results, filter = 'all') {
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';

    const filtered = filter === 'all'
        ? results
        : results.filter(r => r.prediction?.risk_level === filter);

    // Sort: critical first, then high, medium, low
    const order = { critical: 0, high: 1, medium: 2, low: 3 };
    filtered.sort((a, b) =>
        (order[a.prediction?.risk_level] ?? 4) - (order[b.prediction?.risk_level] ?? 4)
    );

    filtered.forEach((r, idx) => {
        const pred = r.prediction || {};
        const prob = pred.dispute_probability || 0;
        const level = pred.risk_level || 'low';
        const disputed = r._ground_truth_disputed;
        const signals = r.triggered_signals || [];

        const row = document.createElement('tr');
        row.setAttribute('data-risk', level);
        row.onclick = () => showDetail(r);

        row.innerHTML = `
            <td style="font-family: monospace; font-size:11px; color: var(--text-primary)">${truncate(r.payment_id, 18)}</td>
            <td style="font-weight:600; color: var(--text-primary)">₹${Number(r.amount).toLocaleString('en-IN')}</td>
            <td>${r.merchant_name || '—'}</td>
            <td>${r.card_network || '—'}</td>
            <td>
                <div style="display:flex;align-items:center;gap:8px;">
                    <div style="width:50px;height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden">
                        <div style="width:${prob * 100}%;height:100%;background:${getColor(level)};border-radius:3px;transition:width 0.5s ease"></div>
                    </div>
                    <span style="font-weight:600;font-size:11px;color:${getColor(level)}">${(prob * 100).toFixed(1)}%</span>
                </div>
            </td>
            <td><span class="risk-badge ${level}">${level}</span></td>
            <td style="font-size:11px">${pred.predicted_dispute_type || '—'}</td>
            <td style="font-size:11px;color:var(--text-muted)">${signals.length} signal${signals.length !== 1 ? 's' : ''}</td>
            <td><span class="truth-badge ${disputed ? 'disputed' : 'clean'}">${disputed ? '⚠ Disputed' : '✓ Clean'}</span></td>
            <td><button class="action-btn" onclick="event.stopPropagation(); showDetail(allResults[${allResults.indexOf(r)}])">Details</button></td>
        `;

        tbody.appendChild(row);
    });
}

function filterResults(filter) {
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    renderResults(allResults, filter);
}

// ── Detail Modal ─────────────────────────────────────────────────────────

function showDetail(result) {
    const modal = document.getElementById('detailModal');
    const title = document.getElementById('modalTitle');
    const body = document.getElementById('modalBody');

    const pred = result.prediction || {};
    const level = pred.risk_level || 'low';

    title.innerHTML = `
        <span style="color:${getColor(level)}">●</span>
        ${result.payment_id}
        <span class="risk-badge ${level}" style="margin-left:8px">${level}</span>
    `;

    let html = '';

    // Transaction info
    html += `<div class="modal-section">
        <h3>Transaction Details</h3>
        <pre>${JSON.stringify({
            payment_id: result.payment_id,
            amount: `₹${result.amount}`,
            merchant: result.merchant_name,
            network: result.card_network,
            dispute_probability: `${(pred.dispute_probability * 100).toFixed(1)}%`,
            predicted_type: pred.predicted_dispute_type,
            model_used: pred.model_used,
            ground_truth: result._ground_truth_disputed ? `DISPUTED (${result._ground_truth_type})` : 'CLEAN',
        }, null, 2)}</pre>
    </div>`;

    // Triggered signals
    const signals = result.triggered_signals || [];
    if (signals.length > 0) {
        html += `<div class="modal-section">
            <h3>Triggered Risk Signals (${signals.length})</h3>
            <div style="margin-bottom:8px">`;
        signals.forEach(s => {
            html += `<span class="signal-tag ${s.severity}">${s.description} (${s.value})</span>`;
        });
        html += `</div></div>`;
    }

    // Deflection
    if (result.deflection) {
        const d = result.deflection;
        html += `<div class="modal-section">
            <h3>🛡️ Pre-Dispute Deflection</h3>
            <pre><strong>Channel:</strong> ${d.channel}
<strong>Urgency:</strong> ${d.timing?.urgency || '—'} (send within ${d.timing?.send_within || '—'})
<strong>Subject:</strong> ${d.subject || '—'}

${d.message}</pre>
        </div>`;
    }

    // Evidence package
    if (result.evidence_package) {
        const e = result.evidence_package;
        html += `<div class="modal-section">
            <h3>📋 Evidence Package</h3>
            <pre><strong>Type:</strong> ${e.template_used}
<strong>Reason Code:</strong> ${e.reason_code} — ${e.reason_code_name}
<strong>Network:</strong> ${e.network}
<strong>Deadline:</strong> ${e.deadline_days} days
<strong>Evidence Strength:</strong> ${e.evidence_strength?.rating} (${(e.evidence_strength?.score * 100).toFixed(0)}%)
<strong>Generated via:</strong> ${e.generation_method}

${e.narrative}</pre>
        </div>`;

        // Evidence checklist
        if (e.evidence_checklist) {
            html += `<div class="modal-section"><h3>Evidence Checklist</h3><div>`;
            e.evidence_checklist.forEach(item => {
                const icon = item.available ? '✅' : '❌';
                html += `<div style="padding:4px 0;font-size:12px;color:var(--text-secondary)">${icon} ${item.item} <span style="color:var(--text-muted)">(${item.source})</span></div>`;
            });
            html += `</div></div>`;
        }
    }

    // Audit trail entry
    html += `<div class="modal-section">
        <h3>Audit Trail Entry</h3>
        <pre>${JSON.stringify(result.audit_entry, null, 2)}</pre>
    </div>`;

    body.innerHTML = html;
    modal.style.display = 'flex';
}

function closeModal(event) {
    if (!event || event.target === document.getElementById('detailModal')) {
        document.getElementById('detailModal').style.display = 'none';
    }
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// ── Helpers ──────────────────────────────────────────────────────────────

function getColor(level) {
    const colors = {
        critical: '#ef4444',
        high: '#f97316',
        medium: '#f59e0b',
        low: '#10b981',
    };
    return colors[level] || '#64748b';
}

function truncate(str, len) {
    if (!str) return '—';
    return str.length > len ? str.slice(0, len) + '…' : str;
}
