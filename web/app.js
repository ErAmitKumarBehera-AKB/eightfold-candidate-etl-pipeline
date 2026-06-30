let inputsData = {};
let rawOutput = [];
let defaultConfig = '';
let currentView = 'cards';

document.addEventListener('DOMContentLoaded', () => {
    loadInitialData();
    document.getElementById('runBtn').addEventListener('click', runPipeline);
    document.getElementById('resetConfigBtn').addEventListener('click', () => {
        document.getElementById('configEditor').value = defaultConfig;
    });
});

async function loadInitialData() {
    try {
        const [configRes, inputsRes] = await Promise.all([
            fetch('/api/config'),
            fetch('/api/inputs')
        ]);
        const configData = await configRes.json();
        defaultConfig = JSON.stringify(configData, null, 2);
        document.getElementById('configEditor').value = defaultConfig;

        inputsData = await inputsRes.json();
        renderSourceBadges();
        renderTabs();
        const first = Object.keys(inputsData)[0];
        if (first) showInput(first);

        document.getElementById('statSources').textContent = `${Object.keys(inputsData).length} sources`;
    } catch (e) {
        console.error('Failed to load data', e);
    }
}

function renderSourceBadges() {
    const el = document.getElementById('sourceBadges');
    el.innerHTML = '';
    Object.keys(inputsData).forEach(name => {
        const span = document.createElement('span');
        span.className = `badge ${getBadgeClass(name)}`;
        span.textContent = name;
        el.appendChild(span);
    });
}

function getBadgeClass(name) {
    if (name.endsWith('.csv')) return 'csv';
    if (name.includes('github')) return 'github';
    return 'json';
}

function renderTabs() {
    const tabs = document.getElementById('inputTabs');
    tabs.innerHTML = '';
    Object.keys(inputsData).forEach((name, i) => {
        const btn = document.createElement('button');
        btn.className = `tab${i === 0 ? ' active' : ''}`;
        btn.textContent = name;
        btn.onclick = () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            showInput(name);
        };
        tabs.appendChild(btn);
    });
}

function showInput(name) {
    const data = inputsData[name];
    document.getElementById('inputContent').textContent =
        typeof data === 'string' ? data : JSON.stringify(data, null, 2);
}

async function runPipeline() {
    const btn = document.getElementById('runBtn');
    const badge = document.getElementById('outputBadge');
    const meta = document.getElementById('runMeta');

    btn.disabled = true;
    btn.classList.add('spinning');
    badge.textContent = 'Running…';
    badge.className = 'output-badge running';
    meta.textContent = '';

    const t0 = performance.now();
    try {
        const config = JSON.parse(document.getElementById('configEditor').value);
        const res = await fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Pipeline failed');
        }

        const result = await res.json();
        rawOutput = result.data;
        const elapsed = ((performance.now() - t0) / 1000).toFixed(2);

        badge.textContent = `${rawOutput.length} profiles`;
        badge.className = 'output-badge success';
        meta.textContent = `Done in ${elapsed}s`;

        document.getElementById('statCandidates').textContent = `${rawOutput.length} candidates`;

        document.getElementById('outputContent').textContent = JSON.stringify(rawOutput, null, 2);
        renderCards(rawOutput);

        switchView(currentView);
    } catch (e) {
        badge.textContent = 'Error';
        badge.className = 'output-badge error';
        document.getElementById('outputContent').textContent = `Error:\n${e.message}`;
        document.getElementById('profileCards').innerHTML =
            `<div class="empty-state"><div class="icon">⚠️</div><p>${e.message}</p></div>`;
        document.getElementById('profileCards').classList.remove('hidden');
        document.getElementById('outputViewer').classList.add('hidden');
        meta.textContent = '';
    } finally {
        btn.disabled = false;
        btn.classList.remove('spinning');
    }
}

function renderCards(profiles) {
    const container = document.getElementById('profileCards');
    if (!profiles || profiles.length === 0) {
        container.innerHTML = `<div class="empty-state"><div class="icon">🔍</div><p>No profiles returned.</p></div>`;
        return;
    }

    container.innerHTML = profiles.map(p => {
        const conf = p.overall_confidence ?? null;
        const confClass = conf === null ? '' : conf >= 0.8 ? 'conf-high' : conf >= 0.6 ? 'conf-med' : 'conf-low';
        const confLabel = conf !== null ? `${(conf * 100).toFixed(0)}% conf` : '—';

        const skills = Array.isArray(p.skills)
            ? p.skills.slice(0, 6).map(s => {
                const name = typeof s === 'string' ? s : s.name;
                const multi = typeof s === 'object' && s.sources && s.sources.length > 1;
                return `<span class="skill-chip ${multi ? 'multi' : ''}" title="${multi ? 'Seen in '+s.sources.join(', ') : ''}">${name}</span>`;
              }).join('')
            : '';

        const sources = p.provenance
            ? [...new Set(Object.values(p.provenance).map(v => v.source))].map(s =>
                `<span class="source-tag ${s.toLowerCase().replace(' ','')}">${s}</span>`).join('')
            : '';

        const employer = p.current_employer ? `<div class="card-meta-item"><span>🏢</span><span>${p.current_employer}</span></div>` : '';
        const location = p.location ? `<div class="card-meta-item"><span>📍</span><span>${p.location}</span></div>` : '';
        const yoe = p.years_experience != null ? `<div class="card-meta-item"><span>⏱</span><span>${p.years_experience}y exp</span></div>` : '';
        const phone = p.phone ? `<div class="card-meta-item"><span>📞</span><span>${p.phone}</span></div>` : '';

        return `<div class="profile-card">
            <div class="card-top">
                <div>
                    <div class="card-name">${p.full_name || '(unnamed)'}</div>
                    <div class="card-email">${p.primary_email || p.emails?.[0] || '—'}</div>
                </div>
                <span class="card-confidence ${confClass}">${confLabel}</span>
            </div>
            ${(employer || location || yoe || phone) ? `<div class="card-meta">${employer}${location}${yoe}${phone}</div>` : ''}
            ${skills ? `<div class="card-skills">${skills}</div>` : ''}
            ${sources ? `<div class="card-sources">${sources}</div>` : ''}
        </div>`;
    }).join('');
}

function switchView(view) {
    currentView = view;
    const cards = document.getElementById('profileCards');
    const json = document.getElementById('outputViewer');
    document.getElementById('btnCards').classList.toggle('active', view === 'cards');
    document.getElementById('btnJson').classList.toggle('active', view === 'json');
    if (view === 'cards') {
        cards.classList.remove('hidden');
        json.classList.add('hidden');
    } else {
        json.classList.remove('hidden');
        cards.classList.add('hidden');
    }
}

function copyOutput() {
    if (!rawOutput.length) return;
    navigator.clipboard.writeText(JSON.stringify(rawOutput, null, 2)).then(() => {
        const btn = document.getElementById('copyBtn');
        btn.textContent = '✓ Copied';
        setTimeout(() => { btn.textContent = '⧉ Copy'; }, 1500);
    });
}
