/**
 * DisputeForge — Dashboard Application
 */

let allResults = [];
let batchMetrics = null;
let isAnalyzingPipeline = false;

// ── Preset Scenarios ──────────────────────────────────

const PRESETS = {
    friendly_fraud: {
        payment_id: "pay_FF_992148",
        order_id: "ord_88412",
        customer_id: "cust_serial_412",
        amount: 8500,
        merchant_name: "QuickMart Electronics",
        merchant_category: "electronics",
        billing_descriptor: "QUICKMART ELEC",
        descriptor_matches_brand: true,
        card_network: "Visa",
        card_country: "IN",
        customer_city: "Mumbai",
        is_digital_goods: false,
        has_tracking: true,
        tracking_number: "BLUEDART-8472910",
        delivery_days: 3,
        delivery_date: "2026-08-18",
        delivery_confirmed: true,
        days_since_delivery: 12,
        contacted_support: false,
        support_contacts_count: 0,
        past_disputes: 3,
        past_disputes_won: 0,
        refund_requested: false,
        refund_status: "none"
    },
    late_delivery: {
        payment_id: "pay_LD_331049",
        order_id: "ord_77190",
        customer_id: "cust_urban_821",
        amount: 2200,
        merchant_name: "Urban Threads",
        merchant_category: "apparel",
        billing_descriptor: "URBAN THREADS",
        descriptor_matches_brand: true,
        card_network: "Mastercard",
        card_country: "IN",
        customer_city: "Bengaluru",
        is_digital_goods: false,
        has_tracking: true,
        tracking_number: "DELHIVERY-99214",
        delivery_days: 16,
        delivery_date: "2026-08-30",
        delivery_confirmed: true,
        days_since_delivery: 1,
        contacted_support: true,
        support_contacts_count: 2,
        past_disputes: 0,
        past_disputes_won: 0,
        refund_requested: true,
        refund_status: "requested"
    },
    clean: {
        payment_id: "pay_CL_109284",
        order_id: "ord_10283",
        customer_id: "cust_prime_102",
        amount: 800,
        merchant_name: "BookNook India",
        merchant_category: "books",
        billing_descriptor: "BOOKNOOK INDIA",
        descriptor_matches_brand: true,
        card_network: "RuPay",
        card_country: "IN",
        customer_city: "Delhi",
        is_digital_goods: false,
        has_tracking: true,
        tracking_number: "EKART-1092834",
        delivery_days: 3,
        delivery_date: "2026-09-01",
        delivery_confirmed: true,
        days_since_delivery: 2,
        contacted_support: false,
        support_contacts_count: 0,
        past_disputes: 0,
        past_disputes_won: 0,
        refund_requested: false,
        refund_status: "none"
    }
};

// ── Boot ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    // Pre-select first scenario for immediate interactive preview
    runPreset('friendly_fraud');
});

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

// ── Interactive Pipeline Demo ────────────────────────

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function runPreset(presetKey) {
    if (isAnalyzingPipeline) return;
    const txn = PRESETS[presetKey];
    if (!txn) return;

    // Update active preset button styling
    document.querySelectorAll('.preset').forEach(b => b.classList.remove('active'));
    const activeBtn = document.getElementById(`preset-${presetKey}`);
    if (activeBtn) activeBtn.classList.add('active');

    // Show pipeline section
    const pipeSec = document.getElementById('pipelineSection');
    pipeSec.style.display = 'block';

    // Populate transaction summary bar
    setText('txnId', txn.payment_id);
    setText('txnAmount', `₹${fmtNum(txn.amount)}`);
    setText('txnMerchant', txn.merchant_name);
    setText('txnNetwork', txn.card_network);
    setText('txnDelivery', txn.delivery_confirmed ? `Delivered (${txn.delivery_days}d)` : 'In Transit');

    isAnalyzingPipeline = true;

    // Reset pipeline UI to pending
    for (let i = 1; i <= 4; i++) {
        const step = document.getElementById(`step${i}`);
        const status = document.getElementById(`step${i}Status`);
        const body = document.getElementById(`step${i}Body`);
        step.className = 'pipe-step pending';
        status.className = 'pipe-step-status';
        status.innerHTML = '';
        body.innerHTML = '';
    }

    try {
        // Send to backend API for live computation
        const res = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(txn)
        });
        const data = await res.json();

        // ── Stage 1: Risk Signals (Rules)
        await setStepRunning(1, 'Extracting signals…');
        await sleep(240);
        renderStep1(data.triggered_signals || []);
        setStepDone(1, `${(data.triggered_signals || []).length} signals found`);

        // ── Stage 2: ML Scoring (XGBoost)
        await setStepRunning(2, 'Scoring via XGBoost…');
        await sleep(220);
        renderStep2(data.prediction || {});
        setStepDone(2, `${((data.prediction?.dispute_probability || 0) * 100).toFixed(1)}% risk`);

        // ── Stage 3a: Deflection (Proactive outreach)
        await setStepRunning(3, 'Evaluating deflection…');
        await sleep(200);
        renderStep3(data.deflection, data.prediction);
        if (data.deflection) {
            setStepDone(3, `Generated (${data.deflection.channel})`);
        } else {
            setStepSkipped(3, 'Skipped (risk < 50%)');
        }

        // ── Stage 3b: Evidence Package (Reason-code Defense)
        await setStepRunning(4, 'Compiling evidence package…');
        await sleep(220);
        renderStep4(data.evidence_package, data.prediction);
        if (data.evidence_package) {
            setStepDone(4, `Ready (${data.evidence_package.reason_code})`);
        } else {
            setStepSkipped(4, 'Skipped (risk < 60%)');
        }

    } catch (err) {
        console.error('Preset analysis failed:', err);
    } finally {
        isAnalyzingPipeline = false;
    }
}

async function setStepRunning(stepNum, label) {
    const step = document.getElementById(`step${stepNum}`);
    const status = document.getElementById(`step${stepNum}Status`);
    step.className = 'pipe-step active';
    status.className = 'pipe-step-status running';
    status.innerHTML = `<span class="spin-mini"></span> ${label}`;
}

function setStepDone(stepNum, label) {
    const step = document.getElementById(`step${stepNum}`);
    const status = document.getElementById(`step${stepNum}Status`);
    step.className = 'pipe-step done';
    status.className = 'pipe-step-status complete';
    status.innerHTML = `✓ ${label}`;
}

function setStepSkipped(stepNum, label) {
    const step = document.getElementById(`step${stepNum}`);
    const status = document.getElementById(`step${stepNum}Status`);
    step.className = 'pipe-step';
    status.className = 'pipe-step-status skipped';
    status.innerHTML = `— ${label}`;
}

function renderStep1(signals) {
    const body = document.getElementById('step1Body');
    if (!signals.length) {
        body.innerHTML = '<div class="pipe-empty-note">No abnormal risk signals triggered. Transaction follows clean purchasing baseline.</div>';
        return;
    }

    const cards = signals.map(s => `
        <div class="pipe-signal-card">
            <span class="pipe-signal-desc">${esc(s.description)}</span>
            <span class="dsignal dsignal--${s.severity}">${s.severity}</span>
        </div>
    `).join('');

    body.innerHTML = `<div class="pipe-signal-grid">${cards}</div>`;
}

function renderStep2(pred) {
    const body = document.getElementById('step2Body');
    const prob = pred.dispute_probability || 0;
    const lvl = pred.risk_level || 'low';
    const disputeType = pred.predicted_dispute_type || 'none';

    body.innerHTML = `
        <div class="pipe-score-box">
            <div class="pipe-score-val" style="color: ${color(lvl)}">${(prob * 100).toFixed(1)}%</div>
            <div class="pipe-score-meta">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span class="risk-ind"><span class="risk-dot risk-dot--${lvl}"></span>${lvl.toUpperCase()} RISK</span>
                    <span style="color:var(--c-text-3)">·</span>
                    <span style="font-size:12px;color:var(--c-text-2)">Predicted type: <strong style="color:var(--c-text)">${disputeType}</strong></span>
                </div>
                <div style="font-size:11px;color:var(--c-text-3)">Model confidence: ${(pred.dispute_type_confidence * 100 || 0).toFixed(0)}% · Features evaluated: 14</div>
            </div>
        </div>
    `;
}

function renderStep3(deflection, pred) {
    const body = document.getElementById('step3Body');
    if (!deflection) {
        body.innerHTML = `<div class="pipe-empty-note">No deflection required. Dispute probability (${((pred?.dispute_probability || 0) * 100).toFixed(1)}%) is below the 50% deflection threshold.</div>`;
        return;
    }

    body.innerHTML = `
        <div class="pipe-message-card">
            <div class="pipe-message-header">
                <span>Channel: <strong>${deflection.channel.toUpperCase()}</strong> · Send within: <strong>${deflection.timing?.send_within || '2 hours'}</strong></span>
                <span>Tone: <strong>${deflection.tone}</strong></span>
            </div>
            <div style="font-size:11px;color:var(--c-text-3);margin-bottom:6px;">Subject: <span style="color:var(--c-text)">${esc(deflection.subject)}</span></div>
            <div class="pipe-message-text">${esc(deflection.message)}</div>
        </div>
    `;
}

function renderStep4(evidence, pred) {
    const body = document.getElementById('step4Body');
    if (!evidence) {
        body.innerHTML = `<div class="pipe-empty-note">No evidence package generated. Dispute probability (${((pred?.dispute_probability || 0) * 100).toFixed(1)}%) is below the 60% evidence preparation threshold.</div>`;
        return;
    }

    const items = (evidence.evidence_checklist || []).map(i => `
        <div class="devidence-item">
            <span class="devidence-check">${i.available ? '✓' : '✗'}</span>
            <span>${esc(i.item)}</span>
            <span class="devidence-src">${esc(i.source)}</span>
        </div>
    `).join('');

    body.innerHTML = `
        <div class="dfield-grid" style="margin-bottom:12px;">
            ${field('Reason code', `${evidence.reason_code} — ${evidence.reason_code_name}`)}
            ${field('Network', evidence.network)}
            ${field('Filing deadline', `${evidence.deadline_days} calendar days`)}
            ${field('Evidence strength', `${evidence.evidence_strength?.rating || 'Strong'} (${((evidence.evidence_strength?.score || 0) * 100).toFixed(0)}%)`)}
        </div>
        <div style="margin-bottom:12px;">
            <div class="dsection-heading">Compiled Evidence Checklist</div>
            <div>${items}</div>
        </div>
        <div>
            <div class="dsection-heading">Bank-Ready Narrative</div>
            <div class="dpre">${esc(evidence.narrative)}</div>
        </div>
    `;
}

// ── Batch Analysis ───────────────────────────────────

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

        document.getElementById('batchResults').style.display = 'block';
        document.getElementById('detailSection').style.display = 'grid';
        document.getElementById('resultsPanel').style.display = 'block';
        document.getElementById('fpBanner').style.display = 'flex';
    } catch (err) {
        console.error(err);
        alert('Batch analysis failed. Is the server running?');
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

function setText(id, v) { 
    const el = document.getElementById(id);
    if (el) el.textContent = v; 
}

function pct(v) { return `${((v || 0) * 100).toFixed(1)}%`; }
function fmtNum(n) { return Number(n || 0).toLocaleString('en-IN'); }

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
