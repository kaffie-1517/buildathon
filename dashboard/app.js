/**
 * DisputeForge — Dashboard
 * Interactive pipeline demo + batch analysis
 */

let allResults = [];
let batchMetrics = null;

// ── Preset transactions (the 3 demo stories) ─────────

const PRESETS = {
    friendly_fraud: {
        label: 'Friendly fraud',
        payment_id: 'pay_RZP8A72K91LX',
        amount: 8500,
        merchant_name: 'QuickMart Electronics',
        billing_descriptor: 'QKMART*ELEC',
        card_network: 'Visa',
        card_country: 'IN',
        delivery_days: 12,
        delivery_confirmed: true,
        has_tracking: true,
        tracking_number: 'BlueDart-874562341',
        delivery_date: '2026-08-18',
        days_since_delivery: 17,
        past_disputes: 3,
        contacted_support: false,
        support_contacts_count: 0,
        refund_requested: true,
        refund_status: 'denied',
        is_digital_goods: false,
        descriptor_matches_brand: false,
        txn_date: '2026-08-06',
    },
    late_delivery: {
        label: 'Late delivery',
        payment_id: 'pay_RZP3M19B55QW',
        amount: 2200,
        merchant_name: 'FashionHub India',
        billing_descriptor: 'FASHIONHUB*IN',
        card_network: 'Mastercard',
        card_country: 'IN',
        delivery_days: 16,
        delivery_confirmed: false,
        has_tracking: true,
        tracking_number: 'Delhivery-993847251',
        delivery_date: null,
        days_since_delivery: 5,
        past_disputes: 0,
        contacted_support: true,
        support_contacts_count: 2,
        refund_requested: false,
        refund_status: 'none',
        is_digital_goods: false,
        descriptor_matches_brand: true,
        txn_date: '2026-08-10',
    },
    clean: {
        label: 'Clean transaction',
        payment_id: 'pay_RZP1C04T22FN',
        amount: 799,
        merchant_name: 'Swiggy Instamart',
        billing_descriptor: 'SWIGGY*INST',
        card_network: 'RuPay',
        card_country: 'IN',
        delivery_days: 1,
        delivery_confirmed: true,
        has_tracking: true,
        tracking_number: 'Dunzo-441827635',
        delivery_date: '2026-08-31',
        days_since_delivery: 4,
        past_disputes: 0,
        contacted_support: false,
        support_contacts_count: 0,
        refund_requested: false,
        refund_status: 'none',
        is_digital_goods: false,
        descriptor_matches_brand: true,
        txn_date: '2026-08-30',
    },
};

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
            el.innerHTML = '<span class="nav-status-dot"></span>Model not trained';
        }
    } catch {
        el.className = 'nav-status error';
        el.innerHTML = '<span class="nav-status-dot"></span>Offline';
    }
}

// ── Preset Scenario ───────────────────────────────────

async function runPreset(key) {
    const txn = PRESETS[key];
    if (!txn) return;

    // Highlight active preset
    document.querySelectorAll('.preset').forEach(b => b.classList.remove('active'));
    document.getElementById(`preset-${key}`).classList.add('active');

    // Show pipeline section
    const pSection = document.getElementById('pipelineSection');
    pSection.style.display = 'block';

    // Reset all steps
    resetSteps();

    // Fill transaction bar
    setText('txnId', shortId(txn.payment_id));
    setText('txnAmount', `₹${fmtNum(txn.amount)}`);
    setText('txnMerchant', txn.merchant_name);
    setText('txnNetwork', txn.card_network);
    setText('txnDelivery', txn.delivery_confirmed ? `Delivered (${txn.delivery_days}d)` : `In transit (${txn.delivery_days}d)`);

    // Scroll to pipeline
    pSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Run pipeline with animated steps
    try {
        setStepActive('step1', 'Extracting signals…');
        await delay(400);

        const res = await fetch('/api/analyze-single', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(txn),
        });
        const data = await res.json();

        renderStep1(data);
        setStepDone('step1', `${data.triggered_signals?.length || 0} signals`);
        await delay(350);

        setStepActive('step2', 'Scoring…');
        await delay(300);
        renderStep2(data);
        const prob = data.prediction?.dispute_probability || 0;
        setStepDone('step2', `${(prob * 100).toFixed(1)}%`);
        await delay(350);

        if (data.deflection) {
            setStepActive('step3', 'Drafting message…');
            await delay(400);
            renderStep3(data.deflection);
            setStepDone('step3', data.deflection.channel);
        } else {
            setStepDone('step3', 'Not needed');
        }
        await delay(300);

        if (data.evidence_package) {
            setStepActive('step4', 'Building evidence…');
            await delay(450);
            renderStep4(data.evidence_package);
            setStepDone('step4', data.evidence_package.evidence_strength?.rating || 'done');
        } else {
            setStepDone('step4', 'Not needed (low risk)');
        }

    } catch (err) {
        console.error(err);
        document.getElementById('step1Status').textContent = 'Error — is the server running?';
    }
}

// ── Step rendering ────────────────────────────────────

function renderStep1(data) {
    const signals = data.triggered_signals || [];
    const body = document.getElementById('step1Body');

    if (signals.length === 0) {
        body.innerHTML = `<div class="signal-grid"><span class="sig-chip sig-chip--clear">No risk signals detected</span></div>`;
    } else {
        const chips = signals.map(s =>
            `<span class="sig-chip sig-chip--${s.severity}" title="${s.value}">${s.description}</span>`
        ).join('');
        body.innerHTML = `<div class="signal-grid">${chips}</div>`;
    }

    expandBody(body);
}

function renderStep2(data) {
    const p = data.prediction || {};
    const prob = p.dispute_probability || 0;
    const lvl = p.risk_level || 'low';
    const body = document.getElementById('step2Body');

    body.innerHTML = `
        <div class="score-display">
            <span class="score-big" style="color:${color(lvl)}">${(prob * 100).toFixed(1)}%</span>
            <div class="score-meta">
                <div class="score-meta-row">Risk level <span>${lvl}</span></div>
                <div class="score-meta-row">Predicted type <span>${p.predicted_dispute_type || '—'}</span></div>
                <div class="score-meta-row">Model <span>${p.model_used || 'xgboost'}</span></div>
            </div>
        </div>
    `;

    expandBody(body);
}

function renderStep3(d) {
    const body = document.getElementById('step3Body');
    body.innerHTML = `
        <div class="msg-meta">
            <span class="msg-meta-item">Channel <b>${d.channel}</b></span>
            <span class="msg-meta-item">Urgency <b>${d.timing?.urgency || '—'}</b></span>
            <span class="msg-meta-item">Send within <b>${d.timing?.send_within || '—'}</b></span>
        </div>
        <div class="msg-box">${esc(d.subject ? `Subject: ${d.subject}\n\n${d.message}` : d.message)}</div>
    `;
    expandBody(body);
}

function renderStep4(e) {
    const body = document.getElementById('step4Body');
    const strength = e.evidence_strength?.rating || '—';
    const score = ((e.evidence_strength?.score || 0) * 100).toFixed(0);

    let checklist = '';
    if (e.evidence_checklist?.length) {
        checklist = e.evidence_checklist.map(i =>
            `<div class="devidence-item"><span class="devidence-check">${i.available ? '✓' : '✗'}</span><span>${esc(i.item)}</span><span class="devidence-src">${esc(i.source)}</span></div>`
        ).join('');
    }

    body.innerHTML = `
        <div class="msg-meta" style="margin-bottom:8px">
            <span class="msg-meta-item">Reason <b>${e.reason_code} — ${e.reason_code_name}</b></span>
            <span class="msg-meta-item">Deadline <b>${e.deadline_days} days</b></span>
            <span class="msg-meta-item">Strength <b>${strength} (${score}%)</b></span>
        </div>
        <div class="msg-box">${esc(e.narrative)}</div>
        ${checklist ? `<div style="margin-top:10px">${checklist}</div>` : ''}
    `;
    expandBody(body);
}

// ── Step state helpers ────────────────────────────────

function resetSteps() {
    ['step1','step2','step3','step4'].forEach(id => {
        const el = document.getElementById(id);
        el.className = 'pipe-step';
        document.getElementById(`${id}Status`).textContent = '';
        const body = document.getElementById(`${id}Body`);
        body.innerHTML = '';
        body.classList.remove('expanded');
    });
}

function setStepActive(id, msg) {
    const el = document.getElementById(id);
    el.className = 'pipe-step step-active';
    document.getElementById(`${id}Status`).textContent = msg;
}

function setStepDone(id, msg) {
    const el = document.getElementById(id);
    el.className = 'pipe-step step-done';
    document.getElementById(`${id}Status`).textContent = msg;
}

function expandBody(body) {
    requestAnimationFrame(() => body.classList.add('expanded'));
}

// ── Batch Analysis ────────────────────────────────────

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
        alert('Batch failed. Is the server running?\n\nRun: python3 -m uvicorn app.main:app --reload');
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
            <td><span class="score-bar">
                <span class="score-track"><span class="score-fill" style="width:${prob*100}%;background:${color(lvl)}"></span></span>
                <span class="score-num" style="color:${color(lvl)}">${(prob*100).toFixed(0)}%</span>
            </span></td>
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

    document.getElementById('drawerTitle').textContent = shortId(result.payment_id);

    const p = result.prediction || {};
    const lvl = p.risk_level || 'low';

    let html = section('Overview', `
        <div class="dfield-grid">
            ${field('Amount', `₹${fmtNum(result.amount)}`)}
            ${field('Merchant', result.merchant_name)}
            ${field('Network', result.card_network)}
            ${field('Model', p.model_used)}
            ${field('Score', `${(p.dispute_probability*100).toFixed(1)}%`)}
            ${field('Level', `<span style="color:${color(lvl)}">${lvl}</span>`)}
            ${field('Type', p.predicted_dispute_type || '—')}
            ${field('Ground truth', result._ground_truth_disputed ? `Disputed (${result._ground_truth_type})` : 'Clean')}
        </div>
    `);

    const sigs = result.triggered_signals || [];
    if (sigs.length) {
        html += section(`Signals (${sigs.length})`, `
            <div class="dsignal-list">
                ${sigs.map(s => `<span class="dsignal dsignal--${s.severity}">${s.description}</span>`).join('')}
            </div>
        `);
    }

    if (result.deflection) {
        const d = result.deflection;
        html += section('Pre-dispute deflection', `
            <div class="dfield-grid">
                ${field('Channel', d.channel)}
                ${field('Urgency', d.timing?.urgency)}
                ${field('Send within', d.timing?.send_within)}
            </div>
            <div class="dpre" style="margin-top:10px">${esc(d.message)}</div>
        `);
    }

    if (result.evidence_package) {
        const e = result.evidence_package;
        html += section('Evidence package', `
            <div class="dfield-grid">
                ${field('Reason', `${e.reason_code} — ${e.reason_code_name}`)}
                ${field('Network', e.network)}
                ${field('Deadline', `${e.deadline_days} days`)}
                ${field('Strength', `${e.evidence_strength?.rating} (${((e.evidence_strength?.score||0)*100).toFixed(0)}%)`)}
            </div>
            <div class="dpre" style="margin-top:10px">${esc(e.narrative)}</div>
            ${e.evidence_checklist?.length ? e.evidence_checklist.map(i =>
                `<div class="devidence-item"><span class="devidence-check">${i.available?'✓':'✗'}</span><span>${esc(i.item)}</span><span class="devidence-src">${esc(i.source)}</span></div>`
            ).join('') : ''}
        `);
    }

    html += section('Audit entry', `<div class="dpre">${JSON.stringify(result.audit_entry, null, 2)}</div>`);

    body.innerHTML = html;
    backdrop.style.display = 'block';
    drawer.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => drawer.classList.add('open'));
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

function section(h, c) { return `<div class="dsection"><div class="dsection-heading">${h}</div>${c}</div>`; }
function field(k, v) { return `<div class="dfield"><div class="dfield-key">${k}</div><div class="dfield-val">${v || '—'}</div></div>`; }
function setText(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }
function pct(v) { return `${((v || 0) * 100).toFixed(1)}%`; }
function fmtNum(n) { return Number(n).toLocaleString('en-IN'); }
function shortId(id) { if (!id) return '—'; return id.length > 16 ? id.slice(0,4)+'…'+id.slice(-8) : id; }
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }
function color(lvl) { return { critical:'#e5484d', high:'#e5884d', medium:'#d4a037', low:'#46a758' }[lvl] || '#606060'; }
function esc(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
