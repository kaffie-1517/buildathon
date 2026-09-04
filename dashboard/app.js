/**
 * DisputeForge — Dashboard
 */

let allResults = [];
let batchMetrics = null;

// ── Boot ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', checkHealth);

async function checkHealth() {
    const el = document.getElementById('modelStatus');
    try {
        const res = await fetch('/api/health');
        const d = await res.json();
        if (d.model_loaded) {
            el.className = 'nav-status ready';
            el.innerHTML = '<span class="nav-status-dot"></span>Model ready';
        } else {
            el.textContent = 'Model not trained';
        }
    } catch {
        el.className = 'nav-status error';
        el.innerHTML = '<span class="nav-status-dot"></span>Offline';
    }
}

// ── Analysis ─────────────────────────────────────────

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
        renderTable(allResults);

        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('resultsContainer').style.display = 'block';
        document.getElementById('detailSection').style.display = 'grid';
        document.getElementById('resultsPanel').style.display = 'block';
        document.getElementById('fpBanner').style.display = 'flex';
    } catch (err) {
        console.error(err);
        alert('Analysis failed. Is the server running?');
    } finally {
        btn.disabled = false;
        loading.style.display = 'none';
    }
}

// ── Metrics ──────────────────────────────────────────

function renderMetrics(m) {
    setText('metricTotal', m.total_transactions || 0);
    setText('metricFlagged', m.flagged_high_risk || 0);
    setText('metricDeflections', m.deflections_generated || 0);
    setText('metricPrecision', pct(m.precision));
    setText('metricRecall', pct(m.recall));
    setText('metricF1', (m.f1_score || 0).toFixed(3));

    setText('cmTN', m.true_negatives || 0);
    setText('cmFP', m.false_alarms || 0);
    setText('cmFN', m.missed_disputes || 0);
    setText('cmTP', m.correctly_flagged || 0);

    setText('fpCostText', m.false_positive_cost || '—');
}

// ── Table ────────────────────────────────────────────

function renderTable(results, filter) {
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';

    let rows = filter && filter !== 'all'
        ? results.filter(r => r.prediction?.risk_level === filter)
        : results;

    const ord = { critical: 0, high: 1, medium: 2, low: 3 };
    rows.sort((a, b) => (ord[a.prediction?.risk_level] ?? 4) - (ord[b.prediction?.risk_level] ?? 4));

    for (const r of rows) {
        const p = r.prediction || {};
        const prob = p.dispute_probability || 0;
        const lvl = p.risk_level || 'low';
        const disputed = r._ground_truth_disputed;

        const tr = document.createElement('tr');
        tr.onclick = () => openDrawer(r);

        tr.innerHTML = `
            <td>${shortId(r.payment_id)}</td>
            <td class="cell-amount">₹${fmtNum(r.amount)}</td>
            <td>${r.merchant_name || '—'}</td>
            <td>${r.card_network || '—'}</td>
            <td>
                <span class="score-bar">
                    <span class="score-track"><span class="score-fill" style="width:${prob * 100}%;background:${color(lvl)}"></span></span>
                    <span class="score-num" style="color:${color(lvl)}">${(prob * 100).toFixed(0)}%</span>
                </span>
            </td>
            <td><span class="risk-ind"><span class="risk-dot risk-dot--${lvl}"></span>${lvl}</span></td>
            <td>${p.predicted_dispute_type || '—'}</td>
            <td><span class="truth ${disputed ? 'truth--yes' : 'truth--no'}">${disputed ? 'Disputed' : 'Clean'}</span></td>
        `;

        tbody.appendChild(tr);
    }
}

function filterResults(filter, btn) {
    document.querySelectorAll('.seg').forEach(s => { s.classList.remove('active'); s.setAttribute('aria-selected', 'false'); });
    btn.classList.add('active');
    btn.setAttribute('aria-selected', 'true');
    renderTable(allResults, filter);
}

// ── Drawer ───────────────────────────────────────────

function openDrawer(result) {
    const drawer = document.getElementById('drawer');
    const backdrop = document.getElementById('drawerBackdrop');
    const body = document.getElementById('drawerBody');
    const title = document.getElementById('drawerTitle');

    const p = result.prediction || {};
    const lvl = p.risk_level || 'low';

    title.textContent = shortId(result.payment_id);

    let html = '';

    // ── Overview
    html += section('Overview', `
        <div class="dfield-grid">
            ${field('Amount', `₹${fmtNum(result.amount)}`)}
            ${field('Merchant', result.merchant_name)}
            ${field('Network', result.card_network)}
            ${field('Model', p.model_used)}
            ${field('Score', `${(p.dispute_probability * 100).toFixed(1)}%`)}
            ${field('Level', lvl)}
            ${field('Type', p.predicted_dispute_type || '—')}
            ${field('Ground truth', result._ground_truth_disputed ? `Disputed (${result._ground_truth_type})` : 'Clean')}
        </div>
    `);

    // ── Signals
    const sigs = result.triggered_signals || [];
    if (sigs.length) {
        let tags = sigs.map(s =>
            `<span class="dsignal dsignal--${s.severity}">${s.description}</span>`
        ).join('');
        html += section(`Signals (${sigs.length})`, `<div class="dsignal-list">${tags}</div>`);
    }

    // ── Deflection
    if (result.deflection) {
        const d = result.deflection;
        html += section('Pre-dispute deflection', `
            <div class="dfield-grid">
                ${field('Channel', d.channel)}
                ${field('Urgency', d.timing?.urgency || '—')}
                ${field('Send within', d.timing?.send_within || '—')}
            </div>
            <div style="margin-top:10px">
                <div class="dsection-heading">Message</div>
                <div class="dpre">${esc(d.message)}</div>
            </div>
        `);
    }

    // ── Evidence
    if (result.evidence_package) {
        const e = result.evidence_package;
        html += section('Evidence package', `
            <div class="dfield-grid">
                ${field('Reason code', `${e.reason_code} — ${e.reason_code_name}`)}
                ${field('Network', e.network)}
                ${field('Deadline', `${e.deadline_days} days`)}
                ${field('Strength', `${e.evidence_strength?.rating} (${(e.evidence_strength?.score * 100).toFixed(0)}%)`)}
            </div>
            <div style="margin-top:10px">
                <div class="dsection-heading">Narrative</div>
                <div class="dpre">${esc(e.narrative)}</div>
            </div>
        `);

        if (e.evidence_checklist?.length) {
            let items = e.evidence_checklist.map(i => `
                <div class="devidence-item">
                    <span class="devidence-check">${i.available ? '✓' : '✗'}</span>
                    <span>${esc(i.item)}</span>
                    <span class="devidence-src">${esc(i.source)}</span>
                </div>
            `).join('');
            html += section('Evidence checklist', items);
        }
    }

    // ── Audit
    html += section('Audit trail', `<div class="dpre">${JSON.stringify(result.audit_entry, null, 2)}</div>`);

    body.innerHTML = html;

    backdrop.style.display = 'block';
    drawer.setAttribute('aria-hidden', 'false');
    requestAnimationFrame(() => drawer.classList.add('open'));
    document.body.style.overflow = 'hidden';
}

function closeDrawer() {
    const drawer = document.getElementById('drawer');
    const backdrop = document.getElementById('drawerBackdrop');

    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';

    setTimeout(() => { backdrop.style.display = 'none'; }, 250);
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDrawer(); });

// ── Helpers ──────────────────────────────────────────

function section(heading, content) {
    return `<div class="dsection"><div class="dsection-heading">${heading}</div>${content}</div>`;
}

function field(key, val) {
    return `<div class="dfield"><div class="dfield-key">${key}</div><div class="dfield-val">${val || '—'}</div></div>`;
}

function setText(id, v) { document.getElementById(id).textContent = v; }
function pct(v) { return `${((v || 0) * 100).toFixed(1)}%`; }
function fmtNum(n) { return Number(n).toLocaleString('en-IN'); }

function shortId(id) {
    if (!id) return '—';
    return id.length > 16 ? id.slice(0, 4) + '…' + id.slice(-8) : id;
}

function color(lvl) {
    return { critical: '#e5484d', high: '#e5884d', medium: '#d4a037', low: '#46a758' }[lvl] || '#606060';
}

function esc(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}
