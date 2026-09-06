/**
 * VeriAlert Interactive Geospatial Command Dashboard Logic
 * Connects to FastAPI REST endpoints and renders Leaflet.js with CartoDB DarkMatter.
 * Handles Phase 6: Regional filtering, mathematical audit breakdown, and live pipeline orchestration.
 */

// Application State
const state = {
  map: null,
  markerLayer: null,
  activeCalamity: 'all',
  activeVeracity: 'all',
  activeRegion: 'all',
  searchQuery: '',
  clusters: [],
  selectedCluster: null,
  pipelinePollingTimer: null
};

// Initial Map Settings (Centered on India & Transboundary Calamity Regions)
const DEFAULT_CENTER = [23.5, 82.0];
const DEFAULT_ZOOM = 5;

// Authenticated CARTO Basemaps API Key
const CARTO_API_KEY = 'cb1_2y6r_1_4449aee82478330890c3942b';

document.addEventListener('DOMContentLoaded', () => {
  initMap();
  initClock();
  setupEventListeners();
  loadDashboardData();
  checkInitialPipelineStatus();
});

/* ==========================================================================
   Map Initialization (Leaflet + CartoDB DarkMatter)
   ========================================================================== */

function initMap() {
  state.map = L.map('disasterMap', {
    zoomControl: false,
    attributionControl: false
  }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);

  L.control.zoom({ position: 'topleft' }).addTo(state.map);

  const tileUrl = CARTO_API_KEY
    ? `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=${encodeURIComponent(CARTO_API_KEY)}`
    : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';

  L.tileLayer(tileUrl, {
    maxZoom: 19,
    subdomains: 'abcd',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>'
  }).addTo(state.map);

  state.markerLayer = L.layerGroup().addTo(state.map);
}

/* ==========================================================================
   Data Fetching & Rendering
   ========================================================================== */

async function loadDashboardData() {
  await Promise.all([
    fetchKPIStats(),
    fetchRegionsList(),
    fetchIncidentClusters()
  ]);
}

async function fetchKPIStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    document.getElementById('statTotalClusters').textContent = data.total_clusters || 0;
    document.getElementById('statTotalReports').textContent = `${data.total_underlying_reports || 0} underlying reports`;
    document.getElementById('statVerified').textContent = data.veracity_breakdown?.verified || 0;
    document.getElementById('statCredible').textContent = data.veracity_breakdown?.credible || 0;
    document.getElementById('statDisputed').textContent = data.veracity_breakdown?.disputed || 0;
  } catch (err) {
    console.error('Failed to load KPI stats:', err);
  }
}

async function fetchRegionsList() {
  const regionSelect = document.getElementById('regionSelect');
  try {
    const res = await fetch('/api/regions');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const previousVal = regionSelect.value;
    regionSelect.innerHTML = '<option value="all">All Regions / States</option>';

    (data.regions || []).forEach(r => {
      const opt = document.createElement('option');
      opt.value = r;
      opt.textContent = r;
      regionSelect.appendChild(opt);
    });

    if (previousVal && Array.from(regionSelect.options).some(o => o.value === previousVal)) {
      regionSelect.value = previousVal;
    }
  } catch (err) {
    console.warn('Failed to load regions list:', err);
  }
}

async function fetchIncidentClusters() {
  const feedEl = document.getElementById('incidentFeed');
  try {
    let url = `/api/alerts?limit=100`;
    if (state.activeCalamity !== 'all') {
      url += `&disaster_type=${encodeURIComponent(state.activeCalamity)}`;
    }
    if (state.activeVeracity !== 'all') {
      url += `&veracity_band=${encodeURIComponent(state.activeVeracity)}`;
    }
    if (state.activeRegion !== 'all') {
      url += `&region=${encodeURIComponent(state.activeRegion)}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const clusters = await res.json();

    state.clusters = clusters;
    renderIncidentFeed(clusters);
    renderMapMarkers(clusters);
  } catch (err) {
    feedEl.innerHTML = `<div class="feed-loading text-red"><i class="fa-solid fa-triangle-exclamation"></i> Error connecting to API: ${err.message}</div>`;
    console.error('Failed to load incident clusters:', err);
  }
}

/* ==========================================================================
   Render Incident Feed Cards
   ========================================================================== */

function renderIncidentFeed(clusters) {
  const feedEl = document.getElementById('incidentFeed');
  const countEl = document.getElementById('visibleCount');

  // Filter based on client-side search query
  const filtered = clusters.filter(c => {
    if (!state.searchQuery) return true;
    const q = state.searchQuery.toLowerCase();
    return (
      (c.event_name && c.event_name.toLowerCase().includes(q)) ||
      (c.location_name && c.location_name.toLowerCase().includes(q)) ||
      (c.summary && c.summary.toLowerCase().includes(q)) ||
      (c.disaster_type && c.disaster_type.toLowerCase().includes(q))
    );
  });

  countEl.textContent = filtered.length;

  if (filtered.length === 0) {
    feedEl.innerHTML = `<div class="feed-loading">No disaster incidents found matching current filters.</div>`;
    return;
  }

  feedEl.innerHTML = '';

  filtered.forEach(c => {
    const card = document.createElement('div');
    const colorClass = getThemeColorClass(c.trust_band);
    card.className = `incident-card theme-${colorClass}`;
    card.setAttribute('data-id', c.id);

    const icon = getDisasterIcon(c.disaster_type);
    const summaryText = c.summary || `${capitalize(c.disaster_type)} reported in ${c.location_name}.`;

    card.innerHTML = `
      <div class="card-top">
        <span class="disaster-badge ${c.disaster_type}">
          <i class="fa-solid ${icon}"></i> ${capitalize(c.disaster_type)}
        </span>
        <span class="veracity-pill ${colorClass}">
          <i class="fa-solid fa-circle-check"></i> ${formatVeracityShort(c.trust_band)} (${Math.round(c.trust_score * 100)}%)
        </span>
      </div>
      <div class="card-title">${escapeHtml(c.event_name)}</div>
      <div class="card-summary">${escapeHtml(summaryText)}</div>
      <div class="card-footer">
        <div class="card-location"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(c.location_name)}</div>
        <div class="card-sources"><i class="fa-solid fa-newspaper"></i> ${c.sources?.length || 1} Sources</div>
      </div>
    `;

    // Click handler: Fly to map + open modal
    card.addEventListener('click', () => {
      focusIncidentOnMap(c);
      openIncidentModal(c.id);
    });

    feedEl.appendChild(card);
  });
}

/* ==========================================================================
   Render Leaflet Map Markers with Pulsing SVG
   ========================================================================== */

function renderMapMarkers(clusters) {
  state.markerLayer.clearLayers();

  clusters.forEach(c => {
    if (!c.latitude || !c.longitude) return;

    const colorClass = getThemeColorClass(c.trust_band);

    const customIcon = L.divIcon({
      className: 'custom-pulsing-marker',
      iconSize: [20, 20],
      iconAnchor: [10, 10],
      popupAnchor: [0, -10],
      html: `
        <div class="marker-container ${colorClass}">
          <div class="pulse-ring"></div>
          <div class="pulse-core"></div>
        </div>
      `
    });

    const marker = L.marker([c.latitude, c.longitude], { icon: customIcon });

    const popupContent = `
      <div class="popup-container">
        <div class="popup-header">
          <span class="disaster-badge ${c.disaster_type}">${capitalize(c.disaster_type)}</span>
          <span class="veracity-pill ${colorClass}">${formatVeracityShort(c.trust_band)}</span>
        </div>
        <div class="popup-title">${escapeHtml(c.event_name)}</div>
        <div class="popup-summary">${escapeHtml(c.summary || '')}</div>
        <button class="popup-btn" onclick="openIncidentModal('${c.id}')">
          <i class="fa-solid fa-calculator"></i> View Trust Audit
        </button>
      </div>
    `;

    marker.bindPopup(popupContent, { maxWidth: 280 });
    state.markerLayer.addLayer(marker);
  });
}

function focusIncidentOnMap(cluster) {
  if (!cluster.latitude || !cluster.longitude) return;
  state.map.flyTo([cluster.latitude, cluster.longitude], 9, {
    duration: 1.2,
    easeLinearity: 0.25
  });
}

/* ==========================================================================
   Deep-Dive Incident Modal with Mathematical Audit Breakdown
   ========================================================================== */

async function openIncidentModal(clusterId) {
  const modal = document.getElementById('incidentModal');
  modal.classList.add('show');

  document.getElementById('modalEventName').textContent = 'Loading Incident Details...';
  document.getElementById('modalAdvisorySummary').textContent = 'Retrieving factual advisory...';
  document.getElementById('modalMemberReports').innerHTML = '<div class="feed-loading">Loading underlying reports...</div>';

  try {
    const res = await fetch(`/api/alerts/${clusterId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.selectedCluster = data;

    // Populate Basic Modal Fields
    document.getElementById('modalDisasterType').textContent = (data.disaster_type || 'DISASTER').toUpperCase();
    document.getElementById('modalEventName').textContent = data.event_name;
    document.getElementById('modalLocation').innerHTML = `<i class="fa-solid fa-location-dot"></i> ${data.location_name}`;
    document.getElementById('modalCoordinates').innerHTML = `<i class="fa-solid fa-compass"></i> ${data.latitude?.toFixed(4)}, ${data.longitude?.toFixed(4)}`;
    document.getElementById('modalReportCount').innerHTML = `<i class="fa-solid fa-newspaper"></i> ${data.member_reports?.length || 0} Reports (${data.sources?.length || 1} Outlets)`;

    // T5 Factual Alert Summary
    document.getElementById('modalAdvisorySummary').textContent = data.summary || 'Emergency advisory under preparation.';

    // Veracity & NLI Summary
    document.getElementById('modalTrustScore').textContent = `${(data.trust_score * 100).toFixed(1)}%`;
    document.getElementById('modalTrustBand').textContent = data.trust_band;
    document.getElementById('modalNliAgreement').textContent = `${((data.nli_agreement_score || 0.85) * 100).toFixed(0)}%`;
    document.getElementById('modalSourceCount').textContent = data.sources?.length || 1;

    // Mathematical Audit Breakdown
    const breakdown = data.trust_score_breakdown;
    if (breakdown && breakdown.components) {
      const sa = breakdown.components.source_authority;
      const cb = breakdown.components.corroboration;
      const cp = breakdown.components.contradiction_penalty;

      document.getElementById('auditSourceAuth').textContent = `${(sa.score * 100).toFixed(1)}%`;
      document.getElementById('auditSourceAuthWeight').textContent = `Weight: 50% → Contribution: +${sa.weighted_value.toFixed(2)}`;
      document.getElementById('auditSourceAuthDesc').textContent = sa.description;

      document.getElementById('auditCorrobFactor').textContent = `${(cb.score * 100).toFixed(1)}%`;
      document.getElementById('auditCorrobWeight').textContent = `Weight: 50% → Contribution: +${cb.weighted_value.toFixed(2)}`;
      document.getElementById('auditCorrobDesc').textContent = cb.description;

      const penaltyVal = cp.penalty_value || 0;
      document.getElementById('auditPenalty').textContent = penaltyVal > 0 ? `-${penaltyVal.toFixed(2)}` : '0.00';
      document.getElementById('auditContraStatus').textContent = cp.has_contradiction ? '⚠️ CONTRADICTION DETECTED' : '✓ No Contradiction';
      document.getElementById('auditPenaltyDesc').textContent = cp.description;

      document.getElementById('auditExplanationText').textContent = breakdown.audit_explanation || 'Audit analysis verified.';
    }

    // Member Reports List
    const reportsListEl = document.getElementById('modalMemberReports');
    reportsListEl.innerHTML = '';

    (data.member_reports || []).forEach(rep => {
      const repItem = document.createElement('div');
      repItem.className = 'member-report-item';
      
      const sourceTag = rep.is_mock ? `${rep.source} (SIMULATED)` : rep.source;
      const urlLink = rep.url ? `<a href="${rep.url}" target="_blank" rel="noopener" class="report-item-url"><i class="fa-solid fa-arrow-up-right-from-square"></i> Open Original Source</a>` : '';

      repItem.innerHTML = `
        <div class="report-item-top">
          <span class="report-item-source"><i class="fa-solid fa-globe"></i> ${escapeHtml(sourceTag)}</span>
          <span class="report-item-date">${formatTimestamp(rep.timestamp)}</span>
        </div>
        <div class="report-item-title">${escapeHtml(rep.title || rep.raw_text?.slice(0, 120))}</div>
        ${urlLink}
      `;
      reportsListEl.appendChild(repItem);
    });

  } catch (err) {
    console.error('Failed to load incident modal detail:', err);
    document.getElementById('modalAdvisorySummary').textContent = 'Error loading incident details.';
  }
}

function closeIncidentModal() {
  document.getElementById('incidentModal').classList.remove('show');
}

/* ==========================================================================
   Pipeline Orchestration & Trigger Modal Handlers
   ========================================================================== */

async function triggerPipelineRun() {
  const btn = document.getElementById('btnRunPipeline');
  btn.classList.add('running');
  btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> <span>Running...</span>`;

  openPipelineModal();

  try {
    const res = await fetch('/api/pipeline/trigger', { method: 'POST' });
    const data = await res.json();
    console.log('Pipeline trigger response:', data);

    startPipelinePolling();
  } catch (err) {
    console.error('Failed to trigger pipeline:', err);
    btn.classList.remove('running');
    btn.innerHTML = `<i class="fa-solid fa-play"></i> <span>Run Pipeline</span>`;
  }
}

function openPipelineModal() {
  const modal = document.getElementById('pipelineProgressModal');
  modal.classList.add('show');
  document.getElementById('btnPipelineDone').style.display = 'none';
  document.getElementById('pipelineModalTitle').textContent = 'Running End-to-End Disaster Pipeline';
  document.getElementById('pipelineProgressFill').style.width = '5%';
  document.getElementById('pipelineProgressPct').textContent = '5% Initializing...';

  // Reset Stepper Badges
  for (let i = 1; i <= 5; i++) {
    const badge = document.getElementById(`stepBadge${i}`);
    if (badge) {
      badge.classList.remove('active', 'completed');
    }
  }
}

function closePipelineModal() {
  document.getElementById('pipelineProgressModal').classList.remove('show');
}

function startPipelinePolling() {
  if (state.pipelinePollingTimer) {
    clearInterval(state.pipelinePollingTimer);
  }

  const startTime = Date.now();

  state.pipelinePollingTimer = setInterval(async () => {
    try {
      const res = await fetch('/api/pipeline/status');
      if (!res.ok) return;
      const status = await res.json();

      updatePipelineUI(status, startTime);

      if (status.status === 'completed' || status.status === 'error') {
        clearInterval(state.pipelinePollingTimer);
        state.pipelinePollingTimer = null;

        const btn = document.getElementById('btnRunPipeline');
        btn.classList.remove('running');
        btn.innerHTML = `<i class="fa-solid fa-play"></i> <span>Run Pipeline</span>`;

        if (status.status === 'completed') {
          document.getElementById('btnPipelineDone').style.display = 'inline-flex';
          // Refresh dashboard data with newly formed clusters
          loadDashboardData();
        }
      }
    } catch (err) {
      console.warn('Pipeline status poll error:', err);
    }
  }, 1000);
}

function updatePipelineUI(status, startTime) {
  const elapsedSec = Math.floor((Date.now() - startTime) / 1000);
  document.getElementById('pipelineElapsedTime').innerHTML = `<i class="fa-solid fa-stopwatch"></i> Elapsed: ${elapsedSec}s`;
  document.getElementById('pipelineCurrentStage').innerHTML = `<i class="fa-solid fa-diagram-project"></i> ${escapeHtml(status.phase_name || 'Processing...')}`;

  const pct = status.progress_percent || 0;
  document.getElementById('pipelineProgressFill').style.width = `${pct}%`;
  document.getElementById('pipelineProgressPct').textContent = `${pct}% — ${status.phase_name}`;

  // Update Header Indicator
  const dot = document.getElementById('statusPulsingDot');
  const label = document.getElementById('orchestratorStatusLabel');
  if (status.status === 'running') {
    dot.className = 'pulsing-dot amber';
    label.textContent = `PIPELINE RUNNING (${pct}%)`;
  } else if (status.status === 'completed') {
    dot.className = 'pulsing-dot green';
    label.textContent = 'PIPELINE UP-TO-DATE';
  }

  // Update 5-Stage Stepper
  const currentPhase = status.current_phase || 0;
  for (let i = 1; i <= 5; i++) {
    const badge = document.getElementById(`stepBadge${i}`);
    if (!badge) continue;
    badge.classList.remove('active', 'completed');
    if (i < currentPhase) {
      badge.classList.add('completed');
    } else if (i === currentPhase) {
      badge.classList.add('active');
    }
  }

  // Render Console Logs
  const consoleLogsEl = document.getElementById('pipelineConsoleLogs');
  if (status.recent_logs && status.recent_logs.length > 0) {
    consoleLogsEl.innerHTML = status.recent_logs.map(log => `
      <div class="log-row ${log.level || 'INFO'}">
        <span class="log-ts">${log.timestamp}</span>
        <span class="log-stage">[${log.stage}]</span>
        <span class="log-msg">${escapeHtml(log.message)}</span>
      </div>
    `).join('');
    consoleLogsEl.scrollTop = consoleLogsEl.scrollHeight;
  }
}

async function checkInitialPipelineStatus() {
  try {
    const res = await fetch('/api/pipeline/status');
    if (res.ok) {
      const status = await res.json();
      if (status.status === 'running') {
        const btn = document.getElementById('btnRunPipeline');
        btn.classList.add('running');
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> <span>Running...</span>`;
        startPipelinePolling();
      }
    }
  } catch {
    // Non-fatal
  }
}

/* ==========================================================================
   UI Event Handlers & Filtering
   ========================================================================== */

function setupEventListeners() {
  // Calamity Filter Pills
  const pills = document.querySelectorAll('#calamityFilterPills .pill');
  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      pills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.activeCalamity = pill.getAttribute('data-type');
      fetchIncidentClusters();
    });
  });

  // Veracity Select Dropdown
  const veracitySelect = document.getElementById('veracitySelect');
  veracitySelect.addEventListener('change', (e) => {
    state.activeVeracity = e.target.value;
    fetchIncidentClusters();
  });

  // Region Select Dropdown
  const regionSelect = document.getElementById('regionSelect');
  regionSelect.addEventListener('change', (e) => {
    state.activeRegion = e.target.value;
    fetchIncidentClusters();
  });

  // Search Input with Debounce
  const searchInput = document.getElementById('searchInput');
  let debounceTimeout = null;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      state.searchQuery = e.target.value.trim();
      renderIncidentFeed(state.clusters);
    }, 200);
  });

  // Reset Map View
  document.getElementById('btnResetMap').addEventListener('click', () => {
    state.map.flyTo(DEFAULT_CENTER, DEFAULT_ZOOM, { duration: 1.0 });
  });

  // Refresh Button
  document.getElementById('btnRefresh').addEventListener('click', () => {
    loadDashboardData();
  });

  // Run Pipeline Button
  document.getElementById('btnRunPipeline').addEventListener('click', triggerPipelineRun);

  // Pipeline Modal Controls
  document.getElementById('pipelineModalCloseBtn').addEventListener('click', closePipelineModal);
  document.getElementById('btnPipelineDone').addEventListener('click', closePipelineModal);

  // Modal Controls
  document.getElementById('modalCloseBtn').addEventListener('click', closeIncidentModal);
  document.getElementById('modalCloseBottomBtn').addEventListener('click', closeIncidentModal);
  document.getElementById('incidentModal').addEventListener('click', (e) => {
    if (e.target.id === 'incidentModal') closeIncidentModal();
  });

  // Modal Fly-To Map Button
  document.getElementById('modalFlyToBtn').addEventListener('click', () => {
    if (state.selectedCluster) {
      closeIncidentModal();
      focusIncidentOnMap(state.selectedCluster);
    }
  });
}

function initClock() {
  const clockEl = document.getElementById('timeDisplay');
  function updateClock() {
    const now = new Date();
    clockEl.textContent = now.toUTCString().slice(17, 25) + ' UTC';
  }
  updateClock();
  setInterval(updateClock, 1000);
}

/* ==========================================================================
   Helpers & Formatters
   ========================================================================== */

function getThemeColorClass(band) {
  if (!band) return 'grey';
  const b = band.toUpperCase();
  if (b.includes('VERIFIED')) return 'green';
  if (b.includes('DISPUTED')) return 'red';
  if (b.includes('CREDIBLE') || b.includes('LIKELY')) return 'amber';
  return 'grey';
}

function formatVeracityShort(band) {
  if (!band) return 'UNVERIFIED';
  const b = band.toUpperCase();
  if (b.includes('VERIFIED')) return 'VERIFIED';
  if (b.includes('DISPUTED')) return 'DISPUTED';
  if (b.includes('CREDIBLE') || b.includes('LIKELY')) return 'DEVELOPING';
  return 'UNVERIFIED';
}

function getDisasterIcon(type) {
  switch ((type || '').toLowerCase()) {
    case 'flood': return 'fa-water';
    case 'landslide': return 'fa-mountain';
    case 'cyclone': return 'fa-hurricane';
    case 'earthquake': return 'fa-house-crack';
    case 'heatwave': return 'fa-temperature-high';
    default: return 'fa-triangle-exclamation';
  }
}

function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatTimestamp(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return isoStr;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
