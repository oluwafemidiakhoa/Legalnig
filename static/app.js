/* ── CounselAI — full client ─────────────────────────────────────────── */
'use strict';

/* ── Auth state ─────────────────────────────────────────────────────────── */
const AUTH = { token: null, user: null };

function saveAuth(token, user) {
  AUTH.token = token; AUTH.user = user;
  localStorage.setItem('lp_token', token);
  localStorage.setItem('lp_user', JSON.stringify(user));
}
function loadAuth() {
  AUTH.token = localStorage.getItem('lp_token');
  const u = localStorage.getItem('lp_user');
  AUTH.user = u ? JSON.parse(u) : null;
}
function clearAuth() {
  AUTH.token = null; AUTH.user = null;
  localStorage.removeItem('lp_token');
  localStorage.removeItem('lp_user');
}

/* ── HTTP helpers ───────────────────────────────────────────────────────── */
async function api(method, path, body) {
  const headers = { 'Content-Type': 'application/json' };
  if (AUTH.token) headers['Authorization'] = 'Bearer ' + AUTH.token;
  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(payload.error || 'Request failed (' + res.status + ')');
  return payload;
}
const apiGet  = (path)        => api('GET',    path);
const apiPost = (path, body)  => api('POST',   path, body);
const apiPut  = (path, body)  => api('PUT',    path, body);

/* ── Escape / format utils ──────────────────────────────────────────────── */
function esc(v) {
  return String(v ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function fmtDate(v) {
  if (!v) return '—';
  const d = new Date(v);
  return isNaN(d) ? v : d.toLocaleDateString('en-NG', { day:'numeric', month:'short', year:'numeric' });
}
function fmtNGN(v) {
  return '₦' + Number(v || 0).toLocaleString('en-NG');
}

/* ── Boot ───────────────────────────────────────────────────────────────── */
function boot() {
  loadAuth();
  if (AUTH.token && AUTH.user) {
    showAppShell();
  } else {
    showAuthShell();
  }
}

function showAuthShell() {
  document.getElementById('auth-shell').style.display = '';
  document.getElementById('app-shell').style.display  = 'none';
  switchAuthTab('login');
}

function showAppShell() {
  document.getElementById('auth-shell').style.display = 'none';
  document.getElementById('app-shell').style.display  = '';
  renderNav();
  const role = AUTH.user?.role;
  if (role === 'lawyer') showView('lawyer-dashboard');
  else if (role === 'admin') showView('admin');
  else showView('dashboard');
}

/* ── Auth tabs ──────────────────────────────────────────────────────────── */
function switchAuthTab(tab) {
  document.getElementById('login-form').style.display    = tab === 'login'    ? '' : 'none';
  document.getElementById('register-form').style.display = tab === 'register' ? '' : 'none';
  document.getElementById('tab-login-btn').classList.toggle('active', tab === 'login');
  document.getElementById('tab-reg-btn').classList.toggle('active', tab === 'register');
}

/* ── Login form ─────────────────────────────────────────────────────────── */
document.getElementById('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  const st = document.getElementById('login-status');
  st.textContent = 'Signing in…';
  try {
    const fd = new FormData(e.target);
    const res = await apiPost('/api/auth/login', { email: fd.get('email'), password: fd.get('password') });
    saveAuth(res.token, res.user);
    st.textContent = '';
    showAppShell();
  } catch(err) {
    st.textContent = err.message;
    st.className = 'status-line error';
  }
});

/* ── Register form ──────────────────────────────────────────────────────── */
document.getElementById('register-form').addEventListener('submit', async e => {
  e.preventDefault();
  const st = document.getElementById('reg-status');
  st.textContent = 'Creating account…';
  try {
    const fd = new FormData(e.target);
    const res = await apiPost('/api/auth/register', {
      email: fd.get('email'),
      display_name: fd.get('display_name'),
      role: fd.get('role'),
      password: fd.get('password')
    });
    saveAuth(res.token, res.user);
    st.textContent = '';
    showAppShell();
  } catch(err) {
    st.textContent = err.message;
    st.className = 'status-line error';
  }
});

/* ── Nav ────────────────────────────────────────────────────────────────── */
const NAV_ITEMS = {
  sme_founder: [
    { id: 'dashboard',   label: 'Dashboard' },
    { id: 'wizard',      label: 'New Matter' },
    { id: 'documents',   label: 'Documents' },
    { id: 'compliance',  label: 'Compliance' },
    { id: 'contracts',   label: 'Contracts' },
    { id: 'billing',     label: 'Billing' },
    { id: 'qa',          label: 'Legal Q&A' },
  ],
  lawyer: [
    { id: 'lawyer-dashboard', label: 'Dashboard' },
    { id: 'documents',        label: 'Documents' },
    { id: 'compliance',       label: 'Compliance' },
    { id: 'contracts',        label: 'Contracts' },
    { id: 'qa',               label: 'Legal Q&A' },
  ],
  admin: [
    { id: 'admin',       label: 'Admin' },
    { id: 'dashboard',   label: 'Founder View' },
    { id: 'lawyer-dashboard', label: 'Lawyer View' },
    { id: 'documents',   label: 'Documents' },
    { id: 'compliance',  label: 'Compliance' },
    { id: 'contracts',   label: 'Contracts' },
    { id: 'billing',     label: 'Billing' },
    { id: 'qa',          label: 'Legal Q&A' },
  ]
};

function renderNav() {
  const role  = AUTH.user?.role || 'sme_founder';
  const items = NAV_ITEMS[role] || NAV_ITEMS.sme_founder;
  document.getElementById('nav-links').innerHTML = items.map(i =>
    `<a class="nav-link" href="#" onclick="showView('${i.id}');return false">${esc(i.label)}</a>`
  ).join('');
  document.getElementById('nav-user').innerHTML =
    `<span>${esc(AUTH.user?.display_name || '')}</span>` +
    `<a class="nav-link" href="#" onclick="logout();return false">Sign out</a>`;
}

async function logout() {
  try { await apiPost('/api/auth/logout', {}); } catch(_) {}
  clearAuth();
  showAuthShell();
}

/* ── View switching ─────────────────────────────────────────────────────── */
let _currentView = null;
const VIEW_LOADERS = {
  'dashboard':        loadDashboard,
  'lawyer-dashboard': loadLawyerDashboard,
  'admin':            loadAdmin,
  'wizard':           initWizard,
  'documents':        loadDocuments,
  'compliance':       loadCompliance,
  'contracts':        loadContracts,
  'billing':          loadBilling,
  'qa':               () => populateMatterSelects('qa-matter-select'),
};

function showView(id) {
  document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
  const el = document.getElementById('view-' + id);
  if (el) el.classList.add('active');
  _currentView = id;
  document.querySelectorAll('.nav-link').forEach(a => {
    a.classList.toggle('active', a.getAttribute('onclick')?.includes("'" + id + "'"));
  });
  if (VIEW_LOADERS[id]) VIEW_LOADERS[id]();
}

/* ── Founder dashboard ──────────────────────────────────────────────────── */
async function loadDashboard() {
  try {
    const [mattersRes, compRes] = await Promise.all([
      apiGet('/api/matters'),
      apiGet('/api/compliance/calendar')
    ]);
    const matters = mattersRes.items || [];
    const obs     = compRes.items || [];

    // metrics
    const overdue  = obs.filter(o => o.status === 'overdue').length;
    const dueSoon  = obs.filter(o => o.status === 'due_soon').length;
    document.getElementById('dash-metrics').innerHTML = [
      { label: 'Active Matters',   value: matters.length },
      { label: 'Overdue',          value: overdue,  badge: overdue  ? 'badge-red'    : '' },
      { label: 'Due Soon (30 d)',   value: dueSoon,  badge: dueSoon  ? 'badge-orange' : '' },
    ].map(m => `<div class="metric-card"><div class="metric-value ${m.badge||''}">${m.value}</div><div class="metric-label">${m.label}</div></div>`).join('');

    // matters list
    document.getElementById('dash-matters').innerHTML = matters.length
      ? matters.slice(0,5).map(renderMatterItem).join('')
      : '<div class="empty">No matters yet — click New Matter to start.</div>';

    // compliance snapshot
    const upcoming = obs.filter(o => ['upcoming','due_soon','overdue'].includes(o.status)).slice(0,5);
    document.getElementById('dash-compliance').innerHTML = upcoming.length
      ? upcoming.map(renderObItem).join('')
      : '<div class="empty">No compliance obligations yet.</div>';
  } catch(err) {
    document.getElementById('dash-matters').innerHTML = `<div class="empty">${esc(err.message)}</div>`;
  }
}

function renderMatterItem(m) {
  return `<div class="queue-item">
    <div style="font-weight:600">${esc(m.entity_name || m.business_name || 'Unnamed matter')}</div>
    <div style="font-size:13px;color:var(--ink-muted)">${esc(m.matter_type || m.entity_type || '')} · ${esc(m.use_case || '')} · ${fmtDate(m.created_at)}</div>
  </div>`;
}

function renderObItem(ob) {
  const badge = ob.status === 'overdue' ? 'badge-red' : ob.status === 'due_soon' ? 'badge-orange' : 'badge-green';
  return `<div class="ob-item">
    <div>
      <div style="font-weight:600">${esc(ob.description)}</div>
      <div style="font-size:13px;color:var(--ink-muted)">Due ${fmtDate(ob.due_date)} · ${esc(ob.obligation_type)}</div>
    </div>
    <span class="badge ${badge}">${esc(ob.status)}</span>
  </div>`;
}

/* ── Lawyer dashboard ───────────────────────────────────────────────────── */
async function loadLawyerDashboard() {
  try {
    const [queueRes, contractsRes] = await Promise.all([
      apiGet('/api/review-queue'),
      apiGet('/api/contracts')
    ]);
    const queue     = queueRes.items || [];
    const contracts = contractsRes.items || [];

    const pending   = queue.filter(q => q.status === 'pending_review').length;
    document.getElementById('lawyer-metrics').innerHTML = [
      { label: 'Pending Review',    value: pending },
      { label: 'Total in Queue',    value: queue.length },
      { label: 'Contracts to review', value: contracts.filter(c => c.status === 'pending_lawyer_review').length },
    ].map(m => `<div class="metric-card"><div class="metric-value">${m.value}</div><div class="metric-label">${m.label}</div></div>`).join('');

    document.getElementById('lawyer-queue').innerHTML = queue.length
      ? queue.map(q => `<div class="queue-item">
          <div style="font-weight:600">${esc(q.entity_name || q.business_name || 'Matter')}</div>
          <div style="font-size:13px;color:var(--ink-muted)">${esc(q.status)} · ${fmtDate(q.updated_at || q.created_at)}</div>
        </div>`).join('')
      : '<div class="empty">Queue is empty.</div>';

    document.getElementById('lawyer-drafts').innerHTML = contracts.filter(c=>c.status==='pending_lawyer_review').length
      ? contracts.filter(c=>c.status==='pending_lawyer_review').map(c =>
          `<div class="queue-item" onclick="showView('contracts')">
            <div style="font-weight:600">${esc(c.filename)}</div>
            <div style="font-size:13px;color:var(--ink-muted)">${fmtDate(c.created_at)}</div>
          </div>`).join('')
      : '<div class="empty">No contracts pending review.</div>';
  } catch(err) {
    document.getElementById('lawyer-queue').innerHTML = `<div class="empty">${esc(err.message)}</div>`;
  }
}

/* ── Admin dashboard ────────────────────────────────────────────────────── */
async function loadAdmin() {
  try {
    const usersRes = await apiGet('/api/users');
    const users = usersRes.items || [];
    document.getElementById('admin-users').innerHTML = users.map(u =>
      `<div class="queue-item">
        <div style="font-weight:600">${esc(u.display_name)} <span class="badge badge-blue">${esc(u.role)}</span></div>
        <div style="font-size:13px;color:var(--ink-muted)">${esc(u.email)} · Joined ${fmtDate(u.created_at)}</div>
      </div>`
    ).join('') || '<div class="empty">No users.</div>';

    const sourcesRes = await apiGet('/api/sources').catch(() => ({ sources: [] }));
    const sources = sourcesRes.sources || [];
    document.getElementById('admin-sources').innerHTML = sources.map(s =>
      `<div class="queue-item">
        <div style="font-weight:600">${esc(s.title)}</div>
        <div style="font-size:13px;color:var(--ink-muted)">${esc(s.source_type)} · ${esc(s.jurisdiction)}</div>
      </div>`
    ).join('') || '<div class="empty">No sources indexed.</div>';
  } catch(err) {
    document.getElementById('admin-users').innerHTML = `<div class="empty">${esc(err.message)}</div>`;
  }
}

async function reindexSources() {
  try {
    await apiPost('/api/sources/reindex', {});
    loadAdmin();
  } catch(err) { alert(err.message); }
}

/* ── Business setup wizard ──────────────────────────────────────────────── */
const WZ = {
  step: 0,
  data: {},
  steps: [
    {
      id: 'entity',
      title: 'Business type',
      fields: [
        { name:'entity_type', label:'Entity type', type:'select', options:[
            {v:'limited_liability_company',l:'Limited Liability Company (LTD)'},
            {v:'business_name',l:'Business Name (Sole/Partnership)'},
            {v:'ngo',l:'NGO / Non-profit'},
          ]},
        { name:'entity_name', label:'Proposed business name', type:'text', placeholder:'Acme Technologies Ltd' },
        { name:'state_of_registration', label:'State of registration', type:'select', options:[
            {v:'Lagos',l:'Lagos'},{v:'Abuja',l:'Abuja (FCT)'},{v:'Rivers',l:'Rivers'},
            {v:'Kano',l:'Kano'},{v:'Ogun',l:'Ogun'},{v:'Other',l:'Other'},
          ]},
      ]
    },
    {
      id: 'use_case',
      title: 'Business activity',
      fields: [
        { name:'use_case', label:'Primary use case', type:'select', options:[
            {v:'general',l:'General business'},{v:'fintech',l:'Fintech / payment services'},
            {v:'health',l:'Healthcare'},{v:'education',l:'Education'},
            {v:'energy',l:'Energy / utilities'},{v:'employment',l:'Staffing / HR'},
            {v:'data_saas',l:'Data / SaaS'},{v:'contracts',l:'Contracts / procurement'},
            {v:'trademark',l:'Brand / trademark'},
          ]},
        { name:'sector', label:'Industry sector', type:'select', options:[
            {v:'technology',l:'Technology'},{v:'finance',l:'Finance'},
            {v:'healthcare',l:'Healthcare'},{v:'manufacturing',l:'Manufacturing'},
            {v:'retail',l:'Retail/Commerce'},{v:'education',l:'Education'},
            {v:'energy',l:'Energy'},{v:'other',l:'Other'},
          ]},
      ]
    },
    {
      id: 'founders',
      title: 'Founders & shareholders',
      fields: [
        { name:'founder_name',  label:'Lead founder name',  type:'text', placeholder:'Adaeze Okonkwo' },
        { name:'founder_email', label:'Founder email',       type:'email', placeholder:'adaeze@example.com' },
        { name:'phone_number',  label:'Phone (optional)',    type:'text', placeholder:'+234 801 234 5678' },
        { name:'estimated_employees', label:'Estimated employees', type:'select', options:[
            {v:'0',l:'Pre-revenue / solo'},{v:'1-5',l:'1–5'},{v:'6-20',l:'6–20'},
            {v:'21-50',l:'21–50'},{v:'51+',l:'51+'},
          ]},
      ]
    },
    {
      id: 'review',
      title: 'Review & submit',
      fields: []
    }
  ]
};

function initWizard() {
  WZ.step = 0;
  WZ.data = {};
  renderWizard();
}

function renderWizard() {
  const step = WZ.steps[WZ.step];
  // Nav dots
  document.getElementById('wizard-steps-nav').innerHTML = WZ.steps.map((s,i) =>
    `<div class="wizard-step ${i < WZ.step ? 'done' : i === WZ.step ? 'active' : ''}">${i+1}. ${esc(s.title)}</div>`
  ).join('');

  const isLast = WZ.step === WZ.steps.length - 1;

  if (isLast) {
    // Review step
    const rows = Object.entries(WZ.data).map(([k,v]) =>
      `<div style="display:flex;gap:12px;margin-bottom:8px"><span style="color:var(--ink-muted);min-width:160px">${esc(k)}</span><span>${esc(v)}</span></div>`
    ).join('');
    document.getElementById('wizard-body').innerHTML =
      `<div style="font-weight:700;font-size:16px;margin-bottom:16px">${esc(step.title)}</div>` +
      `<div>${rows}</div>`;
  } else {
    const html = step.fields.map(f => {
      if (f.type === 'select') {
        const opts = f.options.map(o =>
          `<option value="${esc(o.v)}" ${WZ.data[f.name]===o.v?'selected':''}>${esc(o.l)}</option>`
        ).join('');
        return `<div class="form-group"><label>${esc(f.label)}</label><select name="${f.name}">${opts}</select></div>`;
      }
      return `<div class="form-group"><label>${esc(f.label)}</label><input type="${f.type||'text'}" name="${f.name}" value="${esc(WZ.data[f.name]||'')}" placeholder="${esc(f.placeholder||'')}" /></div>`;
    }).join('');
    document.getElementById('wizard-body').innerHTML =
      `<div style="font-weight:700;font-size:16px;margin-bottom:20px">${esc(step.title)}</div>` + html;
  }

  document.getElementById('btn-prev').style.display = WZ.step > 0 ? '' : 'none';
  document.getElementById('btn-next').textContent = isLast ? 'Submit matter →' : 'Next →';
  document.getElementById('wizard-status').textContent = '';
}

function wizardCollect() {
  const step = WZ.steps[WZ.step];
  step.fields.forEach(f => {
    const el = document.querySelector(`#wizard-body [name="${f.name}"]`);
    if (el) WZ.data[f.name] = el.value.trim();
  });
}

function wizardValidate() {
  const step = WZ.steps[WZ.step];
  for (const f of step.fields) {
    if (f.type !== 'select' && !WZ.data[f.name]) return `Please fill in: ${f.label}`;
  }
  return null;
}

function wizardPrev() {
  if (WZ.step > 0) { WZ.step--; renderWizard(); }
}

async function wizardNext() {
  const isLast = WZ.step === WZ.steps.length - 1;
  if (!isLast) {
    wizardCollect();
    const err = wizardValidate();
    if (err) { document.getElementById('wizard-status').textContent = err; return; }
    WZ.step++;
    renderWizard();
    return;
  }
  // submit
  const st = document.getElementById('wizard-status');
  st.textContent = 'Creating matter…';
  try {
    await apiPost('/api/intakes', {
      entity_type:           WZ.data.entity_type           || 'limited_liability_company',
      business_name:         WZ.data.entity_name           || '',
      use_case:              WZ.data.use_case              || 'general',
      sector:                WZ.data.sector                || 'other',
      founder_name:          WZ.data.founder_name          || '',
      contact_email:         WZ.data.founder_email         || '',
      phone_number:          WZ.data.phone_number          || '',
      state_of_registration: WZ.data.state_of_registration || '',
      estimated_employees:   WZ.data.estimated_employees   || '0',
      jurisdiction:          'Nigeria',
      consent:               true,
    });
    st.textContent = 'Matter created!';
    st.className = 'status-line success';
    setTimeout(() => showView('dashboard'), 1200);
  } catch(err) {
    st.textContent = err.message;
    st.className = 'status-line error';
  }
}

/* ── Document generator ─────────────────────────────────────────────────── */
let _templates = [];

async function loadDocuments() {
  try {
    const res = await apiGet('/api/documents/templates');
    _templates = res.templates || [];
    document.getElementById('template-list').innerHTML = _templates.map(t =>
      `<div class="template-card" onclick="selectTemplate('${esc(t.key)}')">
        <div style="font-weight:700;margin-bottom:4px">${esc(t.title)}</div>
        <div style="font-size:12px;color:var(--ink-muted)">${esc(t.description)}</div>
        <div style="margin-top:8px"><span class="badge badge-blue">${esc(t.tier)}</span></div>
      </div>`
    ).join('') || '<div class="empty">No templates available on your plan.</div>';
  } catch(err) {
    document.getElementById('template-list').innerHTML = `<div class="empty">${esc(err.message)}</div>`;
  }
  await populateMatterSelects('doc-matter-select');
}

async function selectTemplate(key) {
  const tpl = _templates.find(t => t.key === key);
  if (!tpl) return;

  document.getElementById('doc-empty').style.display = 'none';
  document.getElementById('doc-form-panel').style.display = '';
  document.getElementById('doc-form-title').textContent = tpl.title;
  document.getElementById('doc-form-desc').textContent  = tpl.description;
  document.getElementById('doc-preview-panel').style.display = 'none';

  const vars = tpl.variables || [];
  document.getElementById('doc-variables-form').innerHTML = vars.map(v =>
    `<div class="form-group"><label>${esc(v.replace(/_/g,' '))}</label><input id="var-${esc(v)}" placeholder="${esc(v)}" /></div>`
  ).join('');
  document.getElementById('doc-variables-form').dataset.templateKey = key;
}

async function generateDocument() {
  const key     = document.getElementById('doc-variables-form').dataset.templateKey;
  const matterId = document.getElementById('doc-matter-select').value;
  const st      = document.getElementById('doc-gen-status');
  if (!key)      { st.textContent = 'Select a template first.'; return; }
  if (!matterId) { st.textContent = 'Select a matter.'; return; }

  const variables = {};
  document.querySelectorAll('#doc-variables-form input').forEach(el => {
    variables[el.id.replace('var-','')] = el.value;
  });

  st.textContent = 'Generating…';
  try {
    const res = await apiPost('/api/documents/generate', { template_key: key, matter_id: matterId, variables });
    st.textContent = 'Document generated.';
    st.className = 'status-line success';
    const panel = document.getElementById('doc-preview-panel');
    panel.style.display = '';
    document.getElementById('doc-preview-body').textContent = res.document?.body_text || '';
  } catch(err) {
    st.textContent = err.message;
    st.className = 'status-line error';
  }
}

/* ── Compliance calendar ────────────────────────────────────────────────── */
async function loadCompliance() {
  const filter = document.getElementById('compliance-matter-filter').value;
  try {
    const url = filter ? `/api/compliance/calendar?matter_id=${encodeURIComponent(filter)}` : '/api/compliance/calendar';
    const res = await apiGet(url);
    const obs = res.items || [];

    const overdue = obs.filter(o=>o.status==='overdue').length;
    const soon    = obs.filter(o=>o.status==='due_soon').length;
    const done    = obs.filter(o=>o.status==='completed').length;
    document.getElementById('compliance-metrics').innerHTML = [
      {label:'Overdue',   value:overdue, badge: overdue ? 'badge-red'    : ''},
      {label:'Due soon',  value:soon,    badge: soon    ? 'badge-orange' : ''},
      {label:'Completed', value:done,    badge:'badge-green'},
      {label:'Total',     value:obs.length, badge:''},
    ].map(m=>`<div class="metric-card"><div class="metric-value ${m.badge}">${m.value}</div><div class="metric-label">${m.label}</div></div>`).join('');

    document.getElementById('compliance-list').innerHTML = obs.length
      ? obs.map(ob => {
          const badge = ob.status==='overdue' ? 'badge-red' : ob.status==='due_soon' ? 'badge-orange' : ob.status==='completed' ? 'badge-green' : '';
          const btns = ob.status !== 'completed' && ob.status !== 'waived'
            ? `<button class="btn btn-outline btn-sm" onclick="markObComplete('${ob.id}')">Mark done</button>`
            : '';
          return `<div class="ob-item">
            <div>
              <div style="font-weight:600">${esc(ob.description)}</div>
              <div style="font-size:13px;color:var(--ink-muted)">Due ${fmtDate(ob.due_date)} · ${esc(ob.obligation_type)} · ${esc(ob.recurrence)}</div>
              ${ob.notes ? `<div style="font-size:12px;margin-top:4px">${esc(ob.notes)}</div>` : ''}
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px">
              <span class="badge ${badge}">${esc(ob.status)}</span>
              ${btns}
            </div>
          </div>`;
        }).join('')
      : '<div class="empty">No obligations. Generate a calendar for a matter to begin.</div>';

    // populate matter filter
    await populateMatterSelects('compliance-matter-filter', true);
  } catch(err) {
    document.getElementById('compliance-list').innerHTML = `<div class="empty">${esc(err.message)}</div>`;
  }
}

async function markObComplete(id) {
  try {
    await apiPost(`/api/compliance/obligations/${id}/complete`, {});
    loadCompliance();
  } catch(err) { alert(err.message); }
}

function showGenerateCalModal() {
  populateMatterSelects('cal-matter-select');
  document.getElementById('cal-modal-overlay').style.display = 'flex';
}

function hideMod() {
  document.getElementById('cal-modal-overlay').style.display = 'none';
}

async function generateCalendar() {
  const matterId = document.getElementById('cal-matter-select').value;
  const incDate  = document.getElementById('cal-inc-date').value;
  const st       = document.getElementById('cal-modal-status');
  if (!matterId) { st.textContent = 'Select a matter.'; return; }
  st.textContent = 'Generating…';
  try {
    await apiPost('/api/compliance/calendar/generate', { matter_id: matterId, incorporation_date: incDate || null });
    st.textContent = 'Calendar generated!';
    setTimeout(() => { hideMod(); loadCompliance(); }, 1000);
  } catch(err) {
    st.textContent = err.message;
    st.className = 'status-line error';
  }
}

/* ── Contract review ────────────────────────────────────────────────────── */
let _currentContractId = null;

async function loadContracts() {
  await populateMatterSelects('contract-matter-select');
  try {
    const res = await apiGet('/api/contracts');
    const reviews = res.items || [];
    document.getElementById('contracts-list').innerHTML = reviews.length
      ? reviews.map(r => {
          const badge = r.status === 'approved' ? 'badge-green' : r.status === 'pending_lawyer_review' ? 'badge-orange' : '';
          return `<div class="queue-item" onclick="loadContractDetail('${r.id}')">
            <div style="font-weight:600">${esc(r.filename)}</div>
            <div style="font-size:13px;color:var(--ink-muted)">${fmtDate(r.created_at)}</div>
            <span class="badge ${badge}">${esc(r.status)}</span>
          </div>`;
        }).join('')
      : '<div class="empty">No contract reviews yet.</div>';
  } catch(err) {
    document.getElementById('contracts-list').innerHTML = `<div class="empty">${esc(err.message)}</div>`;
  }
}

async function submitContract() {
  const matterId  = document.getElementById('contract-matter-select').value;
  const filename  = document.getElementById('contract-filename').value.trim();
  const rawText   = document.getElementById('contract-text').value.trim();
  const st        = document.getElementById('contract-status');

  if (!matterId) { st.textContent = 'Select a matter.'; return; }
  if (!filename) { st.textContent = 'Enter a filename / description.'; return; }
  if (!rawText)  { st.textContent = 'Paste contract text.'; return; }

  st.textContent = 'Submitting for AI review…';
  st.className = 'status-line';
  try {
    const res = await apiPost('/api/contracts/submit', { matter_id: matterId, filename, raw_text: rawText });
    st.textContent = 'Review complete.';
    st.className = 'status-line success';
    renderContractResult(res.contract_review);
    loadContracts();
  } catch(err) {
    st.textContent = err.message;
    st.className = 'status-line error';
  }
}

async function loadContractDetail(id) {
  try {
    const res = await apiGet(`/api/contracts/${id}`);
    renderContractResult(res.contract_review);
  } catch(err) { alert(err.message); }
}

function renderContractResult(r) {
  if (!r) return;
  _currentContractId = r.id;

  document.getElementById('contract-empty').style.display = 'none';
  document.getElementById('contract-result-panel').style.display = '';

  document.getElementById('contract-summary').textContent = r.ai_summary || 'No summary yet.';

  const flags = Array.isArray(r.risk_flags) ? r.risk_flags : [];
  document.getElementById('contract-risk-flags').innerHTML = flags.length
    ? flags.map(f => {
        const sev = f.severity === 'high' ? 'risk-high' : f.severity === 'medium' ? 'risk-medium' : 'risk-low';
        return `<div class="risk-flag ${sev}">
          <strong>${esc(f.clause_type)}</strong>: ${esc(f.description)}
          ${f.suggestion ? `<div style="margin-top:4px;font-size:12px">Suggestion: ${esc(f.suggestion)}</div>` : ''}
        </div>`;
      }).join('')
    : '<div style="color:var(--ink-muted);font-size:14px">No risk flags detected.</div>';

  const role = AUTH.user?.role;
  const lawyerPanel = document.getElementById('contract-lawyer-panel');
  lawyerPanel.style.display = (role === 'lawyer' || role === 'admin') ? '' : 'none';
}

async function annotateContract() {
  const note = document.getElementById('contract-annotation').value.trim();
  if (!note || !_currentContractId) return;
  try {
    const res = await apiPost(`/api/contracts/${_currentContractId}/annotate`, { annotation: note, clause_ref: 'general', severity: 'medium' });
    renderContractResult(res.contract_review);
    document.getElementById('contract-annotation').value = '';
  } catch(err) { alert(err.message); }
}

async function approveContract() {
  if (!_currentContractId) return;
  if (!confirm('Mark this contract as approved?')) return;
  try {
    const res = await apiPost(`/api/contracts/${_currentContractId}/approve`, {});
    renderContractResult(res.contract_review);
    loadContracts();
  } catch(err) { alert(err.message); }
}

/* ── Billing ────────────────────────────────────────────────────────────── */
let _billingTiers = {};

async function loadBilling() {
  const currentEl  = document.getElementById('billing-current');
  const tierGridEl = document.getElementById('tier-grid');
  const invoiceEl  = document.getElementById('invoice-list');
  currentEl.innerHTML = '<div style="color:var(--ink-muted)">Loading…</div>';

  try {
    const [tiersRes, subRes, invoicesRes] = await Promise.all([
      apiGet('/api/billing/tiers'),
      apiGet('/api/billing/subscription').catch(() => ({})),
      apiGet('/api/billing/invoices').catch(() => ({})),
    ]);
    _billingTiers   = tiersRes.tiers || {};
    const sub       = subRes.subscription || null;
    const billingRecs = subRes.billing_records || invoicesRes.items || [];

    // ── Current plan banner ──────────────────────────────────────────────
    if (sub) {
      const td = _billingTiers[sub.tier] || {};
      currentEl.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
          <div>
            <div style="font-weight:700;font-size:17px;margin-bottom:4px">
              ${esc(td.name || sub.tier)} plan <span class="badge badge-green">${esc(sub.status)}</span>
            </div>
            <div style="color:var(--ink-muted);font-size:14px">
              ${fmtNGN(td.price_ngn || 0)} · Next billing: ${fmtDate(sub.next_billing_at)}
            </div>
          </div>
          <button class="btn btn-outline btn-sm" onclick="cancelSub()">Cancel subscription</button>
        </div>`;
    } else if (billingRecs.length) {
      // One-time purchase (no subscription record)
      const last = billingRecs[0];
      const td   = _billingTiers[last.service_tier] || {};
      currentEl.innerHTML = `
        <div style="font-weight:700;font-size:17px;margin-bottom:4px">
          ${esc(td.name || last.service_tier)} <span class="badge badge-green">Active</span>
        </div>
        <div style="color:var(--ink-muted);font-size:14px">One-time purchase · Paid ${fmtDate(last.created_at)}</div>`;
    } else {
      currentEl.innerHTML = `<div style="color:var(--ink-muted)">No active plan. Choose one below to unlock full access.</div>`;
    }

    // ── Tier grid ────────────────────────────────────────────────────────
    const activeTier = sub?.tier || (billingRecs[0]?.service_tier);
    tierGridEl.innerHTML = Object.entries(_billingTiers).map(([key, t]) => {
      const isActive  = activeTier === key;
      const isOneTime = t.billing_type === 'one_time';
      const isCustom  = !t.price_ngn;
      const priceLabel = isCustom
        ? '<span style="font-size:18px;font-weight:700">Custom</span>'
        : `<span style="font-size:22px;font-weight:700">${fmtNGN(t.price_ngn)}</span>`
          + `<span style="font-size:13px;color:var(--ink-muted)"> ${isOneTime ? 'one-time' : '/ month'}</span>`;

      const btn = isActive
        ? `<div class="badge badge-green" style="text-align:center;padding:10px">Current plan</div>`
        : isCustom
        ? `<a href="mailto:foundryai@getfoundryai.com?subject=Law Firm Plan Enquiry" class="btn btn-outline btn-sm" style="width:100%;text-align:center">Contact us</a>`
        : `<button class="btn btn-primary btn-sm" style="width:100%" onclick="subscribe('${key}',this)">
             Activate ${esc(t.name)}
           </button>`;

      return `<div class="tier-card${isActive ? ' tier-current' : ''}">
        <div class="tier-name">${esc(t.name)}</div>
        <div class="tier-price" style="margin:12px 0">${priceLabel}</div>
        <ul class="tier-features" style="margin-bottom:16px">${(t.features||[]).map(f=>`<li>${esc(f)}</li>`).join('')}</ul>
        ${btn}
      </div>`;
    }).join('');

    // ── Invoice history ──────────────────────────────────────────────────
    invoiceEl.innerHTML = billingRecs.length
      ? billingRecs.map(inv => {
          const badge = inv.status === 'paid' ? 'badge-green' : inv.status === 'pending' ? 'badge-orange' : '';
          return `<div class="queue-item" style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <div style="font-weight:600">${esc(inv.description || inv.service_tier)}</div>
              <div style="font-size:13px;color:var(--ink-muted)">${fmtDate(inv.created_at)}</div>
            </div>
            <div style="text-align:right">
              <div style="font-weight:700">${fmtNGN(inv.amount_ngn)}</div>
              <span class="badge ${badge}">${esc(inv.status)}</span>
            </div>
          </div>`;
        }).join('')
      : '<div style="color:var(--ink-muted);font-size:14px;padding:12px 0">No payment history yet.</div>';

  } catch(err) {
    currentEl.innerHTML = `<div class="empty">${esc(err.message)}</div>`;
  }
}

async function subscribe(tier, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'Processing…'; }
  try {
    // Try Paystack checkout first
    const ps = await apiPost('/api/billing/paystack/initialize', { tier }).catch(() => null);
    if (ps?.authorization_url) {
      window.location.href = ps.authorization_url;
      return;
    }
    // Direct activation (no Paystack configured)
    await apiPost('/api/billing/subscribe', { tier, seat_count: 1 });
    await loadBilling();
    // Scroll to current plan banner
    document.getElementById('billing-current').scrollIntoView({ behavior: 'smooth' });
  } catch(err) {
    if (btn) { btn.disabled = false; btn.textContent = `Activate ${_billingTiers[tier]?.name || tier}`; }
    alert(err.message);
  }
}

async function cancelSub() {
  if (!confirm('Cancel your subscription? This will take effect immediately.')) return;
  try {
    await apiPost('/api/billing/cancel', {});
    loadBilling();
  } catch(err) { alert(err.message); }
}

/* ── Cited Q&A ──────────────────────────────────────────────────────────── */
async function generateAnswer() {
  const matterId = document.getElementById('qa-matter-select').value;
  const question = document.getElementById('qa-question').value.trim();
  const st       = document.getElementById('qa-status');

  if (!question) { st.textContent = 'Enter a question.'; return; }

  st.textContent = 'Generating cited answer…';
  st.className = 'status-line';
  try {
    const res = await apiPost('/api/legal-answer', {
      matter_id:    matterId || null,
      jurisdiction: 'Nigeria',
      question
    });
    st.textContent = '';
    const panel = document.getElementById('qa-result-panel');
    panel.style.display = '';

    document.getElementById('qa-answer-text').innerHTML = esc(res.answer_text || '').replace(/\n/g,'<br>');

    const citations = res.citations || [];
    document.getElementById('qa-citations').innerHTML = citations.length
      ? '<strong>Sources:</strong><br>' + citations.map(c=>
          `<div style="margin-top:4px">· ${esc(c.title)} — ${esc(c.source_type)}</div>`
        ).join('')
      : '';

    document.getElementById('qa-disclaimer').textContent =
      res.disclaimer || 'This answer is AI-generated and should be reviewed by a qualified Nigerian lawyer before acting on it.';
  } catch(err) {
    st.textContent = err.message;
    st.className = 'status-line error';
  }
}

/* ── Populate matter selects ────────────────────────────────────────────── */
async function populateMatterSelects(selectId, keepFirst = false) {
  try {
    const res = await apiGet('/api/matters');
    const matters = res.items || [];
    const el = document.getElementById(selectId);
    if (!el) return;
    const firstOpt = keepFirst ? el.options[0]?.outerHTML || '' : '';
    el.innerHTML = firstOpt + matters.map(m =>
      `<option value="${esc(m.id)}">${esc(m.title || m.entity_name || m.business_name || m.id)}</option>`
    ).join('');
  } catch(_) {}
}

/* ── Init ───────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', boot);
