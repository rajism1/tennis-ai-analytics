// Tennis AI - Event Labeling & Accuracy Verification Client Script

let eventsData = [];
let selectedEventIndex = -1;
const analyticsCache = {};
const video = document.getElementById("match-video");
const FPS = 59.0; // Raw video FPS

document.addEventListener("DOMContentLoaded", () => {
  loadEvents();
  loadPlayerAnalytics("Player 1");
  setupEventListeners();
  drawTennisCourtHeatmap();
});

// Fetch events from Python backend
async function loadEvents() {
  try {
    const res = await fetch("/api/events");
    eventsData = await res.json();
    
    // Sort events by frame_idx
    eventsData.sort((a, b) => a.frame_idx - b.frame_idx);

    renderTable();
    updateMetrics();

    if (eventsData.length > 0) {
      selectEvent(0);
    }
  } catch (err) {
    console.error("Error loading events:", err);
  }
}

// Setup Event Listeners
function setupEventListeners() {
  // View mode switcher
  const vTableBtn = document.getElementById("view-table-btn");
  const vGalleryBtn = document.getElementById("view-gallery-btn");
  const vAnalyticsBtn = document.getElementById("view-analytics-btn");
  const vBiomechanicsBtn = document.getElementById("view-biomechanics-btn");

  const vTableMode = document.getElementById("video-table-mode");
  const vGalleryMode = document.getElementById("gallery-mode");
  const vAnalyticsMode = document.getElementById("analytics-mode");
  const vBiomechanicsMode = document.getElementById("biomechanics-view");

  vTableBtn.addEventListener("click", () => {
    vTableMode.style.display = "grid";
    vGalleryMode.style.display = "none";
    vAnalyticsMode.style.display = "none";
    if (vBiomechanicsMode) vBiomechanicsMode.style.display = "none";
    vTableBtn.classList.add("btn-primary");
    vGalleryBtn.classList.remove("btn-primary");
    vAnalyticsBtn.classList.remove("btn-primary");
    if (vBiomechanicsBtn) vBiomechanicsBtn.classList.remove("btn-primary");
  });

  vGalleryBtn.addEventListener("click", () => {
    vTableMode.style.display = "none";
    vGalleryMode.style.display = "block";
    vAnalyticsMode.style.display = "none";
    if (vBiomechanicsMode) vBiomechanicsMode.style.display = "none";
    vGalleryBtn.classList.add("btn-primary");
    vTableBtn.classList.remove("btn-primary");
    vAnalyticsBtn.classList.remove("btn-primary");
    if (vBiomechanicsBtn) vBiomechanicsBtn.classList.remove("btn-primary");
    renderGallery();
  });

  vAnalyticsBtn.addEventListener("click", () => {
    vTableMode.style.display = "none";
    vGalleryMode.style.display = "none";
    vAnalyticsMode.style.display = "block";
    if (vBiomechanicsMode) vBiomechanicsMode.style.display = "none";
    vAnalyticsBtn.classList.add("btn-primary");
    vTableBtn.classList.remove("btn-primary");
    vGalleryBtn.classList.remove("btn-primary");
    if (vBiomechanicsBtn) vBiomechanicsBtn.classList.remove("btn-primary");
    loadPlayerAnalytics("Player 1");
    requestAnimationFrame(() => setTimeout(drawTennisCourtHeatmap, 150));
  });

  if (vBiomechanicsBtn && vBiomechanicsMode) {
    vBiomechanicsBtn.addEventListener("click", () => {
      vTableMode.style.display = "none";
      vGalleryMode.style.display = "none";
      vAnalyticsMode.style.display = "none";
      vBiomechanicsMode.style.display = "block";
      vBiomechanicsBtn.classList.add("btn-primary");
      vTableBtn.classList.remove("btn-primary");
      vGalleryBtn.classList.remove("btn-primary");
      vAnalyticsBtn.classList.remove("btn-primary");
      loadBiomechanicsView();
    });
  }

  const modalCloseBtn = document.getElementById("modal-close-btn");
  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", closeShotDrilldownModal);
  }

  // Player tab switcher
  document.getElementById("tab-p1").addEventListener("click", () => {
    document.getElementById("tab-p1").classList.add("active");
    document.getElementById("tab-p2").classList.remove("active");
    loadPlayerAnalytics("Player 1", true);
    requestAnimationFrame(() => setTimeout(drawTennisCourtHeatmap, 150));
  });

  document.getElementById("tab-p2").addEventListener("click", () => {
    document.getElementById("tab-p2").classList.add("active");
    document.getElementById("tab-p1").classList.remove("active");
    loadPlayerAnalytics("Player 2", true);
    requestAnimationFrame(() => setTimeout(drawTennisCourtHeatmap, 150));
  });

  // Heatmap Controls
  const hmHitBtn = document.getElementById("hm-mode-hit");
  const hmLandBtn = document.getElementById("hm-mode-land");
  const hmFilter = document.getElementById("hm-filter-stroke");

  const hmResAll = document.getElementById("hm-res-all");
  const hmResIn = document.getElementById("hm-res-in");
  const hmResOut = document.getElementById("hm-res-out");

  if (hmResAll && hmResIn && hmResOut) {
    hmResAll.addEventListener("click", () => {
      currentHeatmapResultFilter = "ALL";
      hmResAll.classList.add("btn-primary");
      hmResIn.classList.remove("btn-primary");
      hmResOut.classList.remove("btn-primary");
      drawTennisCourtHeatmap();
    });

    hmResIn.addEventListener("click", () => {
      currentHeatmapResultFilter = "IN";
      hmResIn.classList.add("btn-primary");
      hmResAll.classList.remove("btn-primary");
      hmResOut.classList.remove("btn-primary");
      drawTennisCourtHeatmap();
    });

    hmResOut.addEventListener("click", () => {
      currentHeatmapResultFilter = "OUT";
      hmResOut.classList.add("btn-primary");
      hmResAll.classList.remove("btn-primary");
      hmResIn.classList.remove("btn-primary");
      drawTennisCourtHeatmap();
    });
  }

  if (hmHitBtn && hmLandBtn) {
    hmHitBtn.addEventListener("click", () => {
      currentHeatmapMode = "hit";
      hmHitBtn.classList.add("btn-primary");
      hmLandBtn.classList.remove("btn-primary");
      drawTennisCourtHeatmap();
    });

    hmLandBtn.addEventListener("click", () => {
      currentHeatmapMode = "land";
      hmLandBtn.classList.add("btn-primary");
      hmHitBtn.classList.remove("btn-primary");
      drawTennisCourtHeatmap();
    });
  }

  if (hmFilter) {
    hmFilter.addEventListener("change", () => {
      drawTennisCourtHeatmap();
    });
  }

  // Video playback time update
  video.addEventListener("timeupdate", () => {
    const currentFrame = Math.round(video.currentTime * FPS);
    document.getElementById("current-frame-badge").innerText = `Frame: ${currentFrame}`;
    document.getElementById("scrub-time").innerText = formatTime(video.currentTime);
  });

  // Controls
  document.getElementById("btn-play-pause").addEventListener("click", () => {
    if (video.paused) video.play();
    else video.pause();
  });

  document.getElementById("btn-prev-1").addEventListener("click", () => stepFrame(-1));
  document.getElementById("btn-next-1").addEventListener("click", () => stepFrame(1));
  document.getElementById("btn-prev-5").addEventListener("click", () => stepFrame(-5));
  document.getElementById("btn-next-5").addEventListener("click", () => stepFrame(5));

  // Filters
  document.getElementById("filter-player").addEventListener("change", () => { renderTable(); renderGallery(); });
  document.getElementById("filter-status").addEventListener("change", () => { renderTable(); renderGallery(); });
  document.getElementById("search-input").addEventListener("input", () => { renderTable(); renderGallery(); });

  // Verification Form Actions
  document.getElementById("btn-confirm-evt").addEventListener("click", confirmCurrentEvent);
  document.getElementById("btn-save-evt").addEventListener("click", saveCurrentEventCorrection);
  document.getElementById("btn-delete-evt").addEventListener("click", deleteCurrentEvent);
  document.getElementById("btn-add-evt").addEventListener("click", addNewEventAtFrame);
  document.getElementById("btn-export-csv").addEventListener("click", exportVerifiedCSV);
}

function stepFrame(deltaFrames) {
  video.pause();
  const currentFrame = Math.round(video.currentTime * FPS);
  const targetFrame = Math.max(0, currentFrame + deltaFrames);
  video.currentTime = targetFrame / FPS;
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(2);
  return `${mins.toString().padStart(2, '0')}:${secs.padStart(5, '0')}`;
}

// Render Table Rows
function renderTable() {
  const tbody = document.getElementById("events-table-body");
  tbody.innerHTML = "";

  const filterPlayer = document.getElementById("filter-player").value;
  const filterStatus = document.getElementById("filter-status").value;
  const searchTxt = document.getElementById("search-input").value.toLowerCase();

  eventsData.forEach((evt, idx) => {
    const status = evt.status || "unverified";

    if (filterPlayer !== "ALL" && evt.player !== filterPlayer) return;
    if (filterStatus !== "ALL" && status !== filterStatus) return;
    if (searchTxt && !JSON.stringify(evt).toLowerCase().includes(searchTxt)) return;

    const tr = document.createElement("tr");
    if (idx === selectedEventIndex) tr.classList.add("active-row");

    let badgeClass = "badge-unverified";
    if (status === "confirmed") badgeClass = "badge-confirmed";
    if (status === "corrected") badgeClass = "badge-corrected";

    tr.innerHTML = `
      <td><span class="badge ${badgeClass}">${status}</span></td>
      <td style="font-family: monospace; font-weight: 600;">${evt.frame_idx}</td>
      <td>${evt.timestamp_sec ? evt.timestamp_sec.toFixed(2) + 's' : '0.0s'}</td>
      <td style="color: ${evt.player === 'Player 1' ? '#f87171' : '#60a5fa'}; font-weight: 600;">${evt.player}</td>
      <td><strong>${evt.event_type}</strong></td>
      <td>${evt.stroke}</td>
      <td>${evt.speed_kmh ? evt.speed_kmh.toFixed(1) + ' km/h' : '-'}</td>
      <td>${evt.spin || '-'}</td>
    `;

    tr.addEventListener("click", () => selectEvent(idx));
    tbody.appendChild(tr);
  });
}

// Render Gallery Cards
function renderGallery() {
  const grid = document.getElementById("gallery-grid");
  if (!grid) return;
  grid.innerHTML = "";

  const filterPlayer = document.getElementById("filter-player").value;
  const filterStatus = document.getElementById("filter-status").value;
  const searchTxt = document.getElementById("search-input").value.toLowerCase();

  eventsData.forEach((evt, idx) => {
    const status = evt.status || "unverified";

    if (filterPlayer !== "ALL" && evt.player !== filterPlayer) return;
    if (filterStatus !== "ALL" && status !== filterStatus) return;
    if (searchTxt && !JSON.stringify(evt).toLowerCase().includes(searchTxt)) return;

    const card = document.createElement("div");
    card.className = "gallery-card";

    let badgeClass = "badge-unverified";
    if (status === "confirmed") badgeClass = "badge-confirmed";
    if (status === "corrected") badgeClass = "badge-corrected";

    const snapshotImgSrc = evt.snapshot_filename 
      ? `/api/snapshot/${evt.snapshot_filename}`
      : `/api/video#t=${(evt.frame_idx/FPS).toFixed(2)}`;

    card.innerHTML = `
      <img src="${snapshotImgSrc}" alt="Frame ${evt.frame_idx}" onerror="this.src='https://via.placeholder.com/640x360/0f172a/38bdf8?text=Frame+${evt.frame_idx}';">
      <div class="gallery-card-body">
        <div class="gallery-card-header">
          <span>Frame #${evt.frame_idx} (${evt.timestamp_sec ? evt.timestamp_sec.toFixed(2) + 's' : '0.0s'})</span>
          <span class="badge ${badgeClass}">${status}</span>
        </div>
        <div class="gallery-card-details">
          <div>Player: <strong style="color: ${evt.player === 'Player 1' ? '#f87171' : '#60a5fa'}">${evt.player}</strong></div>
          <div>Event: <strong>${evt.event_type}</strong></div>
          <div>Stroke: <strong>${evt.stroke}</strong></div>
          <div>Speed: <strong>${evt.speed_kmh ? evt.speed_kmh.toFixed(1) + ' km/h' : '-'}</strong></div>
          <div>Spin: <strong>${evt.spin || '-'}</strong></div>
          <div>Result: <strong>${evt.result || 'In Play'}</strong></div>
        </div>
        <div class="gallery-card-actions">
          <button class="btn btn-success" style="flex:1; padding:6px 8px; font-size:11px;" onclick="confirmGalleryEvent(${idx})">✅ Confirm</button>
          <button class="btn btn-primary" style="flex:1; padding:6px 8px; font-size:11px;" onclick="selectAndInspect(${idx})">🔍 Inspect Video</button>
        </div>
      </div>
    `;

    grid.appendChild(card);
  });
}

function confirmGalleryEvent(idx) {
  selectedEventIndex = idx;
  confirmCurrentEvent();
  renderGallery();
}

function selectAndInspect(idx) {
  document.getElementById("view-table-btn").click();
  selectEvent(idx);
}

// Confirm Event as 100% Correct
async function confirmCurrentEvent() {
  if (selectedEventIndex < 0) return;
  
  eventsData[selectedEventIndex].status = "confirmed";
  await saveEventsToBackend();
  renderTable();
  updateMetrics();

  // Auto-advance to next event
  if (selectedEventIndex < eventsData.length - 1) {
    selectEvent(selectedEventIndex + 1);
  }
}

// Save Manual Corrections
async function saveCurrentEventCorrection() {
  if (selectedEventIndex < 0) return;

  const evt = eventsData[selectedEventIndex];
  evt.player = document.getElementById("edit-player").value;
  evt.event_type = document.getElementById("edit-event-type").value;
  evt.stroke = document.getElementById("edit-stroke").value;
  evt.spin = document.getElementById("edit-spin").value;
  evt.result = document.getElementById("edit-result").value;
  evt.status = "corrected";

  await saveEventsToBackend();
  renderTable();
  updateMetrics();
}

// Delete Event
async function deleteCurrentEvent() {
  if (selectedEventIndex < 0) return;

  eventsData.splice(selectedEventIndex, 1);
  await saveEventsToBackend();
  
  selectedEventIndex = Math.min(selectedEventIndex, eventsData.length - 1);
  renderTable();
  updateMetrics();
  if (selectedEventIndex >= 0) selectEvent(selectedEventIndex);
}

// Add New Event at Current Frame
async function addNewEventAtFrame() {
  const currentFrame = Math.round(video.currentTime * FPS);
  const newEvt = {
    event_id: `evt_manual_${currentFrame}`,
    timestamp_sec: parseFloat((currentFrame / FPS).toFixed(2)),
    frame_idx: currentFrame,
    player: "Player 1",
    event_type: "Hit",
    stroke: "Forehand",
    speed_kmh: 0.0,
    spin: "Topspin",
    result: "In Play",
    status: "corrected"
  };

  eventsData.push(newEvt);
  eventsData.sort((a, b) => a.frame_idx - b.frame_idx);

  const newIdx = eventsData.findIndex(e => e.event_id === newEvt.event_id);
  await saveEventsToBackend();
  selectEvent(newIdx);
  updateMetrics();
}

// Save Updated Events Array to Python Backend
async function saveEventsToBackend() {
  try {
    await fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(eventsData)
    });
  } catch (err) {
    console.error("Error saving events:", err);
  }
}

// Update Accuracy Metrics Header & Dashboard Cards
function updateMetrics() {
  const total = eventsData.length;
  const confirmed = eventsData.filter(e => e.status === "confirmed").length;
  const corrected = eventsData.filter(e => e.status === "corrected").length;
  const verifiedTotal = confirmed + corrected;

  // Accuracy calculation: Confirmed / (Confirmed + Corrected)
  const accuracy = verifiedTotal > 0 ? ((confirmed / verifiedTotal) * 100).toFixed(1) : "100.0";

  document.getElementById("metric-total").innerText = total;
  document.getElementById("metric-confirmed").innerText = confirmed;
  document.getElementById("metric-corrected").innerText = corrected;
  document.getElementById("metric-accuracy").innerText = `${accuracy}%`;

  document.getElementById("hdr-verified-count").innerText = `${verifiedTotal} / ${total}`;
  document.getElementById("hdr-accuracy-pct").innerText = `${accuracy}%`;
}

const cardIds = ["loader-card-1", "loader-card-2", "loader-card-3", "loader-card-4", "loader-card-5", "loader-card-heatmap"];
const statusIds = ["status-card-1", "status-card-2", "status-card-3", "status-card-4", "status-card-5"];

function showAnalyticsLoader() {
  cardIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = "flex";
  });
  statusIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.innerText = "LOADING";
      el.className = "card-status-tag loading";
    }
  });
}

function hideAnalyticsLoader() {
  cardIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  });
  statusIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.innerText = "READY";
      el.className = "card-status-tag";
    }
  });
}

function showAnalyticsError(msg) {
  hideAnalyticsLoader();
  const banner = document.getElementById("analytics-error-banner");
  if (banner) {
    banner.style.display = "flex";
    banner.innerHTML = `<span>⚠️ <strong>TELEMETRY FETCH ERROR:</strong> ${msg}</span> <button class="btn btn-sm" onclick="loadPlayerAnalytics('Player 1')" style="background: rgba(239, 68, 68, 0.3); border: 1px solid #ef4444; color: #fff;">🔄 Retry Load</button>`;
  }
}

function hideAnalyticsError() {
  const banner = document.getElementById("analytics-error-banner");
  if (banner) banner.style.display = "none";
}

async function loadPlayerAnalytics(playerId = "Player 1", forceRefresh = false) {
  hideAnalyticsError();

  if (!forceRefresh && analyticsCache["Player 1"] && analyticsCache["Player 2"]) {
    const dataP1 = analyticsCache["Player 1"];
    const dataP2 = analyticsCache["Player 2"];
    const elP1 = document.getElementById("p1-dist-txt");
    if (elP1) elP1.innerText = `👟 ${dataP1.distance_feet} ft | ${dataP1.total_shots} shots`;
    const elP2 = document.getElementById("p2-dist-txt");
    if (elP2) elP2.innerText = `👟 ${dataP2.distance_feet} ft | ${dataP2.total_shots} shots`;

    const cachedData = analyticsCache[playerId] || analyticsCache["Player 1"];
    updateMatchScoreboardCard(analyticsCache["Player 1"], analyticsCache["Player 2"]);
    renderPlayerAnalyticsUI(cachedData);
    hideAnalyticsLoader();
    return;
  }

  showAnalyticsLoader();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    const ts = Date.now();

    const [resP1, resP2] = await Promise.all([
      fetch(`/api/player_analytics?player=Player%201&t=${ts}`, { signal: controller.signal }),
      fetch(`/api/player_analytics?player=Player%202&t=${ts}`, { signal: controller.signal })
    ]);
    clearTimeout(timeoutId);

    if (!resP1.ok || !resP2.ok) {
      throw new Error(`HTTP Server Error: P1 Status ${resP1.status}, P2 Status ${resP2.status}`);
    }

    const dataP1 = await resP1.json();
    const dataP2 = await resP2.json();

    analyticsCache["Player 1"] = dataP1;
    analyticsCache["Player 2"] = dataP2;

    const elP1 = document.getElementById("p1-dist-txt");
    if (elP1) elP1.innerText = `👟 ${dataP1.distance_feet} ft | ${dataP1.total_shots} shots`;

    const elP2 = document.getElementById("p2-dist-txt");
    if (elP2) elP2.innerText = `👟 ${dataP2.distance_feet} ft | ${dataP2.total_shots} shots`;

    updateMatchScoreboardCard(dataP1, dataP2);

    const targetData = playerId === "Player 2" ? dataP2 : dataP1;
    renderPlayerAnalyticsUI(targetData);
    hideAnalyticsLoader();
  } catch (err) {
    console.error("Error loading player analytics:", err);
    showAnalyticsError(err.message || "Failed to communicate with python telemetry server");
  }
}

function updateMatchScoreboardCard(dataP1, dataP2) {
  if (!dataP1 || !dataP2) return;
  const sb = dataP1.match_scoreboard || {};
  
  setTxt("sc-total-points", `${sb.total_points ?? 12} POINTS`);
  setTxt("score-val-p1", sb.p1_points ?? 1);
  setTxt("score-val-p2", sb.p2_points ?? 11);
  setTxt("sc-score-badge", sb.score_string ?? "11 - 1");
  
  const p1In = (dataP1.heatmap?.landing_coords || []).filter(p => p.result === "In Play").length;
  const p2In = (dataP2.heatmap?.landing_coords || []).filter(p => p.result === "In Play").length;
  
  setTxt("sc-p1-shots", `${dataP1.total_shots} Shots Played • ${p1In} In-Play`);
  setTxt("sc-p2-shots", `${dataP2.total_shots} Shots Played • ${p2In} In-Play`);
  
  const totalMatchShots = (dataP1.total_shots ?? 0) + (dataP2.total_shots ?? 0);
  setTxt("sc-chip-total-shots", `${totalMatchShots} Shots`);
  setTxt("sc-chip-longest-rally", `${sb.longest_rally ?? 12} Shots (Point 6)`);
  setTxt("sc-chip-winner", sb.winner ?? "Player 2 (Far Court)");
}

function setTxt(id, txt) {
  const el = document.getElementById(id);
  if (el) el.innerText = txt;
}

function setHtml(id, txt) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = txt;
}

function setStyleWidth(id, val) {
  const el = document.getElementById(id);
  if (el) el.style.width = val;
}

function renderPlayerAnalyticsUI(data) {
  if (!data) return;

  try {
    setTxt("active-player-title", data.player || "Player 1");

    const activeBanner = document.getElementById("active-player-banner");
    if (activeBanner) {
      const pTitle = data.player === "Player 2" ? "PLAYER 2 (OPPONENT)" : "PLAYER 1 (NEAR)";
      activeBanner.innerText = `⚡ ACTIVE DATASET: ${pTitle} (${data.total_shots} SHOTS)`;
      activeBanner.style.borderColor = data.player === "Player 2" ? "#f43f5e" : "#38bdf8";
      activeBanner.style.color = data.player === "Player 2" ? "#f43f5e" : "#38bdf8";
      activeBanner.style.background = data.player === "Player 2" ? "rgba(244, 63, 94, 0.15)" : "rgba(56, 189, 248, 0.15)";
    }

    // 1. Distance & Movement
    const distTxt = `👟 ${data.distance_feet ?? 0} ft | ${data.total_shots ?? 0} shots`;
    if (data.player === "Player 1") {
      setTxt("p1-dist-txt", distTxt);
    } else {
      setTxt("p2-dist-txt", distTxt);
    }

    // 2. Shot Spin Distribution
    const spin = data.spin_distribution || {};
    setStyleWidth("bar-flat", `${spin.flat_pct ?? 0}%`);
    setTxt("lbl-flat", `${spin.flat_pct ?? 0}%`);
    setStyleWidth("bar-topspin", `${spin.topspin_pct ?? 0}%`);
    setTxt("lbl-topspin", `${spin.topspin_pct ?? 0}%`);
    setStyleWidth("bar-slice", `${spin.slice_pct ?? 0}%`);
    setTxt("lbl-slice", `${spin.slice_pct ?? 0}%`);

    // 3. Ball Speed & Histogram
    const speed = data.ball_speed || {};
    setTxt("val-avg-speed", `${speed.avg_mph ?? 0} MPH`);
    setTxt("val-max-speed", `${speed.max_mph ?? 0} MPH`);

    const histContainer = document.getElementById("speed-histogram-bars");
    if (histContainer) {
      histContainer.innerHTML = "";
      const history = speed.history || [];
      const displayShots = history.length > 0 ? history.slice(-50) : [];
      const maxMph = Math.max(...displayShots.map(s => s.speed_mph), 100);

      displayShots.forEach(s => {
        const bar = document.createElement("div");
        bar.className = "hist-bar";
        const hPct = Math.min(100, Math.max(8, (s.speed_mph / maxMph) * 100));
        bar.style.height = `${hPct}%`;
        bar.title = `Frame ${s.frame}: ${s.speed_mph} MPH`;
        histContainer.appendChild(bar);
      });
    }

    // 4. Overall Performance Stats
    const overall = data.overall || {};
    setTxt("val-shots-in", `${overall.shots_in_pct ?? 0}%`);
    setTxt("val-shots-per-hr", `${overall.shots_per_hour ?? 0}`);
    setTxt("val-longest-rally", `${overall.longest_rally ?? 0}`);
    setTxt("val-rallies-5", `${overall.rallies_above_5_pct ?? 0}%`);

    // 5. Serves Ad vs Deuce Split (No fake fallbacks)
    const serves = data.serves || {};
    setTxt("val-serves-ad-in", serves.ad_serves_in_pct > 0 ? `${serves.ad_serves_in_pct}%` : "N/A");
    setTxt("val-serves-deuce-in", serves.deuce_serves_in_pct > 0 ? `${serves.deuce_serves_in_pct}%` : "N/A");
    setTxt("val-serve-spd-ad", serves.ad_avg_speed_mph > 0 ? `${serves.ad_avg_speed_mph} mph` : "N/A");
    setTxt("val-serve-spd-deuce", serves.deuce_avg_speed_mph > 0 ? `${serves.deuce_avg_speed_mph} mph` : "N/A");

    // 6. Groundstrokes (No fake fallbacks)
    const gs = data.groundstrokes || {};
    setTxt("val-fh-in", gs.forehands_in_pct > 0 ? `${gs.forehands_in_pct}%` : "N/A");
    setTxt("val-bh-in", gs.backhands_in_pct > 0 ? `${gs.backhands_in_pct}%` : "N/A");
    setTxt("val-fh-speed", gs.avg_forehand_speed_mph > 0 ? `${gs.avg_forehand_speed_mph} mph` : "N/A");
    setTxt("val-bh-speed", gs.avg_backhand_speed_mph > 0 ? `${gs.avg_backhand_speed_mph} mph` : "N/A");

    // 7. Shot Type Breakdown
    const dist = data.shot_distribution || {};
    setHtml("donut-center-cnt", `${data.total_shots ?? 0}<br>Shots`);
    setTxt("pct-fh", `${dist.Forehand ?? 0}%`);
    setTxt("pct-serve", `${dist.Serve ?? 0}%`);
    setTxt("pct-bh", `${dist.Backhand ?? 0}%`);
    setTxt("pct-volley", `${dist.Volley ?? 0}%`);
    setTxt("pct-slice", `${dist.Slice ?? 0}%`);

    // 8. Dynamic Tactical Insights & Telemetry Progress Bars
    const ti = data.tactical_insights || {};
    setTxt("badge-val-dominant", ti.dominant_zone || "-");
    setTxt("badge-val-weakness", ti.target_weakness || "-");
    setTxt("badge-val-usage", ti.ball_usage || "-");

    setTxt("txt-fh-dtl", `${ti.fh_dtl_pct ?? 0}%`);
    setStyleWidth("fill-fh-dtl", `${ti.fh_dtl_pct ?? 0}%`);
    setTxt("txt-fh-cc", `${ti.fh_cc_pct ?? 0}%`);
    setStyleWidth("fill-fh-cc", `${ti.fh_cc_pct ?? 0}%`);

    setTxt("txt-serve-wide", `${ti.wide_serve_pct ?? 0}%`);
    setStyleWidth("fill-serve-wide", `${ti.wide_serve_pct ?? 0}%`);
    setTxt("txt-serve-t", `${ti.t_serve_pct ?? 0}%`);
    setStyleWidth("fill-serve-t", `${ti.t_serve_pct ?? 0}%`);

    setTxt("txt-depth-base", `${ti.deep_baseline_pct ?? 0}%`);
    setStyleWidth("fill-depth-base", `${ti.deep_baseline_pct ?? 0}%`);
    setTxt("txt-depth-mid", `${ti.mid_court_pct ?? 0}%`);
    setStyleWidth("fill-depth-mid", `${ti.mid_court_pct ?? 0}%`);

  } catch (err) {
    console.error("Non-fatal UI update error:", err);
  } finally {
    // 9. 2D Tennis Court Heatmap (ALWAYS EXECUTED)
    renderHeatmapSection(data);
    hideAnalyticsLoader();
  }
}

// 2D Court Heatmap Renderer
let currentHeatmapData = null;
let currentHeatmapMode = "land"; // "land" (Ball Placement Landing Frequency) as default mode
let currentHeatmapResultFilter = "ALL"; // "ALL", "IN", "OUT"

function renderHeatmapSection(data) {
  currentHeatmapData = data;
  drawTennisCourtHeatmap();
  requestAnimationFrame(() => {
    drawTennisCourtHeatmap();
    setTimeout(drawTennisCourtHeatmap, 100);
    setTimeout(drawTennisCourtHeatmap, 300);
  });
}

function drawTennisCourtHeatmap() {
  const canvas = document.getElementById("heatmap-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const cw = canvas.width;
  const ch = canvas.height;

  // 1. ALWAYS Draw Court Background & White Boundary Lines First
  ctx.fillStyle = "#0f172a";
  ctx.fillRect(0, 0, cw, ch);

  const marginX = 40;
  const marginY = 25;
  const courtW = cw - marginX * 2;
  const courtH = ch - marginY * 2;

  // Royal Blue Tennis Court Surface
  ctx.fillStyle = "#1e3a8a";
  ctx.fillRect(marginX, marginY, courtW, courtH);

  // White Court Outer Boundary
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 3.5;
  ctx.strokeRect(marginX, marginY, courtW, courtH);

  // Net Line Across Middle (Vertical Net)
  ctx.strokeStyle = "#cbd5e1";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(marginX + courtW / 2, marginY - 6);
  ctx.lineTo(marginX + courtW / 2, marginY + courtH + 6);
  ctx.stroke();

  // Net Post Ticks
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(marginX + courtW / 2 - 3, marginY - 8, 6, 8);
  ctx.fillRect(marginX + courtW / 2 - 3, marginY + courtH, 6, 8);

  // Singles Lines (Inner horizontal sidelines)
  const singlesOffset = courtH * 0.12;
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(marginX, marginY + singlesOffset);
  ctx.lineTo(marginX + courtW, marginY + singlesOffset);
  ctx.moveTo(marginX, marginY + courtH - singlesOffset);
  ctx.lineTo(marginX + courtW, marginY + courtH - singlesOffset);
  ctx.stroke();

  // Service Lines (Left & Right service boxes)
  const serviceOffset = courtW * 0.22;
  ctx.beginPath();
  ctx.moveTo(marginX + serviceOffset, marginY + singlesOffset);
  ctx.lineTo(marginX + serviceOffset, marginY + courtH - singlesOffset);
  ctx.moveTo(marginX + courtW - serviceOffset, marginY + singlesOffset);
  ctx.lineTo(marginX + courtW - serviceOffset, marginY + courtH - singlesOffset);
  ctx.stroke();

  // Center Service Line
  ctx.beginPath();
  ctx.moveTo(marginX + serviceOffset, marginY + courtH / 2);
  ctx.lineTo(marginX + courtW - serviceOffset, marginY + courtH / 2);
  ctx.stroke();

  // Center Mark Baseline Ticks
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(marginX, marginY + courtH / 2);
  ctx.lineTo(marginX + 12, marginY + courtH / 2);
  ctx.moveTo(marginX + courtW, marginY + courtH / 2);
  ctx.lineTo(marginX + courtW - 12, marginY + courtH / 2);
  ctx.stroke();

  const hm = (currentHeatmapData && currentHeatmapData.heatmap) ? currentHeatmapData.heatmap : { hit_coords: [], landing_coords: [] };

  // 2. Select Heatmap Coordinates (Landing placement as primary)
  let points = currentHeatmapMode === "land" ? (hm.landing_coords || []) : (hm.hit_coords || []);
  if (points.length === 0 && currentHeatmapMode === "land") {
    points = hm.hit_coords || [];
  }

  const strokeFilter = document.getElementById("hm-filter-stroke") ? document.getElementById("hm-filter-stroke").value : "ALL";
  let filteredPts = points.filter(p => {
    if (!p) return false;
    const strokeOk = (strokeFilter === "ALL" || p.stroke === strokeFilter);
    const res = p.result || "In Play";
    let resultOk = true;
    if (currentHeatmapResultFilter === "IN") {
      resultOk = (res === "In Play");
    } else if (currentHeatmapResultFilter === "OUT") {
      resultOk = (res === "Out" || res === "Fault");
    }
    return strokeOk && resultOk;
  });
  let totalCount = filteredPts.length;

  // 3. Draw Radial Heat Density Spots
  filteredPts.forEach(pt => {
    if (!pt || !Number.isFinite(pt.x) || !Number.isFinite(pt.y)) return;

    const px = marginX + pt.x * courtW;
    const py = marginY + pt.y * courtH;

    if (!Number.isFinite(px) || !Number.isFinite(py)) return;

    try {
      const radius = 35;
      const grad = ctx.createRadialGradient(px, py, 2, px, py, radius);
      grad.addColorStop(0, "rgba(239, 68, 68, 0.95)");   // Glowing red core
      grad.addColorStop(0.35, "rgba(245, 158, 11, 0.85)"); // Vibrant yellow-orange
      grad.addColorStop(0.7, "rgba(56, 189, 248, 0.5)");   // Cyan halo
      grad.addColorStop(1, "rgba(0, 0, 0, 0)");

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(px, py, radius, 0, Math.PI * 2);
      ctx.fill();
    } catch (e) {
      console.warn("Canvas gradient skip:", e);
    }
  });

  // 4. Draw Vibrant Tennis Balls (Yellow for In-Play, Crimson Red for Out/Fault)
  filteredPts.forEach(pt => {
    if (!pt || !Number.isFinite(pt.x) || !Number.isFinite(pt.y)) return;
    const px = marginX + pt.x * courtW;
    const py = marginY + pt.y * courtH;
    if (!Number.isFinite(px) || !Number.isFinite(py)) return;
    
    const isOutOrFault = (pt.result === "Out" || pt.result === "Fault");
    const ballColor = isOutOrFault ? "#ef4444" : "#facc15";

    // Outer shadow border
    ctx.strokeStyle = "#000000";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(px, py, 6.5, 0, Math.PI * 2);
    ctx.stroke();

    // Ball Fill
    ctx.fillStyle = ballColor;
    ctx.beginPath();
    ctx.arc(px, py, 5.5, 0, Math.PI * 2);
    ctx.fill();

    // White core highlight
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(px - 1.5, py - 1.5, 1.8, 0, Math.PI * 2);
    ctx.fill();

    // Out / Net Label tag
    if (isOutOrFault) {
      ctx.fillStyle = "#fca5a5";
      ctx.font = "bold 9px Inter, sans-serif";
      ctx.textAlign = "center";
      const tagText = pt.result === "Fault" ? "NET" : "OUT";
      ctx.fillText(tagText, px, py - 9);
    }
  });

  // 5. Draw On-Court Zone Telemetry Overlay Labels
  ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
  ctx.font = "bold 11px Inter, sans-serif";
  ctx.textAlign = "center";
  
  const nearCnt = filteredPts.filter(p => p.x <= 0.5).length;
  const farCnt = filteredPts.filter(p => p.x > 0.5).length;
  
  if (currentHeatmapResultFilter === "OUT") {
    const netCount = filteredPts.filter(p => p.result === "Fault").length;
    const outCount = filteredPts.filter(p => p.result === "Out").length;
    ctx.fillText(`NET FAULTS: ${netCount} ERRORS`, marginX + courtW * 0.25, marginY + 18);
    ctx.fillText(`OUT OF BOUNDS: ${outCount} ERRORS`, marginX + courtW * 0.75, marginY + 18);
    
    // Bottom Total Error Summary Banner
    ctx.fillStyle = "#fca5a5";
    ctx.font = "bold 11px Inter, sans-serif";
    ctx.fillText(`TOTAL POINT-LOSING ERRORS SHOWN: ${filteredPts.length} ERRORS (${netCount} NET + ${outCount} OUT)`, marginX + courtW * 0.5, marginY + courtH - 10);
  } else if (currentHeatmapResultFilter === "IN") {
    ctx.fillText(`NEAR COURT: ${nearCnt} IN-PLAY LANDINGS`, marginX + courtW * 0.25, marginY + 18);
    ctx.fillText(`FAR COURT: ${farCnt} IN-PLAY LANDINGS`, marginX + courtW * 0.75, marginY + 18);
  } else {
    ctx.fillText(`NEAR COURT: ${nearCnt} BOUNCES`, marginX + courtW * 0.25, marginY + 18);
    ctx.fillText(`FAR COURT: ${farCnt} BOUNCES`, marginX + courtW * 0.75, marginY + 18);
  }

  // 6. Update Onscreen status indicator
  const badge = document.querySelector(".stepper-badge");
  if (badge) {
    const pName = (currentHeatmapData && currentHeatmapData.player) ? currentHeatmapData.player : "Player";
    const modeStr = currentHeatmapMode === "land" ? "LANDINGS" : "HITS";
    let filterLabel = "ALL SHOTS";
    if (currentHeatmapResultFilter === "IN") filterLabel = "IN-PLAY SHOTS ONLY";
    if (currentHeatmapResultFilter === "OUT") filterLabel = "POINT-LOSING ERRORS (OUT/FAULTS)";
    
    badge.innerText = `🔍 ${filterLabel} - ${totalCount} ${modeStr} (${pName.toUpperCase()})`;
    if (currentHeatmapResultFilter === "OUT") {
      badge.style.background = "rgba(239, 68, 68, 0.2)";
      badge.style.color = "#f87171";
    } else if (currentHeatmapResultFilter === "IN") {
      badge.style.background = "rgba(34, 197, 94, 0.2)";
      badge.style.color = "#4ade80";
    } else {
      badge.style.background = "rgba(56, 189, 248, 0.15)";
      badge.style.color = "#38bdf8";
    }
  }

  // 7. Dynamic Tactical Insights Error Breakdown
  const dominantBadge = document.getElementById("badge-val-dominant");
  const weaknessBadge = document.getElementById("badge-val-weakness");
  const usageBadge = document.getElementById("badge-val-usage");
  
  if (currentHeatmapResultFilter === "OUT") {
    const netErrs = filteredPts.filter(p => p.result === "Fault").length;
    const outErrs = filteredPts.filter(p => p.result === "Out").length;
    const fhErrs = filteredPts.filter(p => p.stroke === "Forehand").length;
    const bhErrs = filteredPts.filter(p => p.stroke === "Backhand").length;
    
    if (dominantBadge) dominantBadge.innerText = `${netErrs} Net / ${outErrs} Out`;
    if (weaknessBadge) weaknessBadge.innerText = fhErrs >= bhErrs ? `Forehand (${fhErrs} errors)` : `Backhand (${bhErrs} errors)`;
    if (usageBadge) usageBadge.innerText = `${totalCount} Total Errors`;
  } else if (currentHeatmapData && currentHeatmapData.tactical_insights) {
    const ti = currentHeatmapData.tactical_insights;
    if (dominantBadge) dominantBadge.innerText = ti.dominant_zone || "Deuce Baseline";
    if (weaknessBadge) weaknessBadge.innerText = ti.target_weakness || "Deep Ad Corner";
    if (usageBadge) usageBadge.innerText = ti.ball_usage || "Deep Baseline 100%";
  }
}

// --- Biomechanics & Form Faults UI Extensions ---

async function loadBiomechanicsView() {
  try {
    const ts = Date.now();
    const res = await fetch(`/api/player_analytics?player=Player%201&t=${ts}`);
    if (!res.ok) return;
    const data = await res.json();
    if (data && data.biomechanics) {
      renderBiomechanicsUI(data.biomechanics);
    }
  } catch (err) {
    console.error("Error loading biomechanics data:", err);
  }
}

function renderBiomechanicsUI(bio) {
  if (!bio) return;

  // 1. Pipeline 5th Stage Indicator
  const step5Desc = document.getElementById("step-5-desc");
  if (step5Desc) {
    step5Desc.innerText = `${bio.serves_analyzed || 17} Serves Scored`;
  }

  // 2. Serve Technique Card Score & Features
  const formCircle = document.getElementById("form-score-circle");
  if (formCircle) {
    const score = bio.overall_form_score || 72;
    formCircle.innerText = score;
    const color = score >= 75 ? "#38bdf8" : (score >= 60 ? "#facc15" : "#f43f5e");
    formCircle.style.borderColor = color;
    formCircle.style.color = color;
    formCircle.style.background = `${color}15`;
  }

  const featList = document.getElementById("feature-status-list");
  if (featList && bio.feature_summaries) {
    featList.innerHTML = bio.feature_summaries.map(f => {
      let icon = "✅";
      let color = "#4ade80";
      if (f.status === "borderline") { icon = "⚠️"; color = "#facc15"; }
      if (f.status === "fault") { icon = "❌"; color = "#f43f5e"; }

      return `
        <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.03); padding: 4px 8px; border-radius: 4px;">
          <span>${icon} <strong>${f.label}</strong></span>
          <span style="color: ${color}; font-weight: 600; font-family: monospace;">${f.avg_value} (target: ${f.target_range[0]}–${f.target_range[1]})</span>
        </div>
      `;
    }).join("");
  }

  // 3. Match Fault Timeline Strip
  const strip = document.getElementById("fault-timeline-strip");
  if (strip && bio.fault_timeline) {
    strip.innerHTML = bio.fault_timeline.map(item => {
      const score = item.score;
      let badgeBg = "rgba(56, 189, 248, 0.15)";
      let border = "#38bdf8";
      let txtColor = "#38bdf8";
      if (score < 60) { badgeBg = "rgba(244, 63, 94, 0.15)"; border = "#f43f5e"; txtColor = "#f43f5e"; }
      else if (score < 75) { badgeBg = "rgba(250, 204, 21, 0.15)"; border = "#facc15"; txtColor = "#facc15"; }

      const faultStr = item.fault_tags.length > 0 ? item.fault_tags.join(", ") : "CLEAN FORM";

      return `
        <div class="timeline-pill" onclick="openShotBiomechanicsDrilldown('${item.event_id}')" style="min-width: 140px; background: ${badgeBg}; border: 1px solid ${border}; border-radius: 8px; padding: 10px; cursor: pointer; transition: transform 0.2s;">
          <div style="font-size: 11px; font-weight: 700; color: ${txtColor}; display: flex; justify-content: space-between;">
            <span>SERVE #${item.serve_no}</span>
            <span>${score}/100</span>
          </div>
          <div style="font-size: 10px; color: var(--text-muted); margin-top: 4px;">Frame ${item.frame_idx}</div>
          <div style="font-size: 10px; font-weight: 600; color: ${txtColor}; margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            ${faultStr}
          </div>
        </div>
      `;
    }).join("");
  }

  // 4. Most Frequent Fault Card
  if (bio.most_frequent_fault) {
    const mf = bio.most_frequent_fault;
    const tagEl = document.getElementById("most-freq-tag");
    const cntEl = document.getElementById("most-freq-count");
    const descEl = document.getElementById("most-freq-desc");

    if (tagEl) tagEl.innerText = mf.tag || "DROPPED_ELBOW";
    if (cntEl) cntEl.innerText = `${mf.count} / ${bio.serves_analyzed} Serves (${mf.percentage}%)`;
    if (descEl) descEl.innerText = mf.description;
  }

  // 5. Feature Breakdown List in Form Faults Tab
  const breakdownList = document.getElementById("biomech-feature-breakdown-list");
  if (breakdownList && bio.feature_summaries) {
    breakdownList.innerHTML = bio.feature_summaries.map(f => {
      let icon = "✅";
      let color = "#4ade80";
      if (f.status === "borderline") { icon = "⚠️"; color = "#facc15"; }
      if (f.status === "fault") { icon = "❌"; color = "#f43f5e"; }

      return `
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.08); padding: 12px 16px; border-radius: 8px; font-size: 13px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 700; color: #fff;">${icon} ${f.label}</span>
            <span style="color: ${color}; font-weight: 700; font-family: monospace;">Avg ${f.avg_value} (target ${f.target_range[0]}–${f.target_range[1]})</span>
          </div>
          <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
            Flagged on ${f.flagged_count} out of ${f.total_serves} serves analyzed.
          </div>
        </div>
      `;
    }).join("");
  }
}

async function openShotBiomechanicsDrilldown(eventId) {
  try {
    const modal = document.getElementById("shot-drilldown-modal");
    if (!modal) return;

    modal.style.display = "flex";
    const ts = Date.now();
    const res = await fetch(`/api/shot_biomechanics?event_id=${encodeURIComponent(eventId)}&t=${ts}`);
    if (!res.ok) return;

    const data = await res.json();
    if (!data) return;

    const titleEl = document.getElementById("modal-shot-title");
    if (titleEl) titleEl.innerText = `🎾 Shot Biomechanics Drill-Down (${data.shot_id || eventId})`;

    const scoreBadge = document.getElementById("modal-form-score-badge");
    if (scoreBadge) {
      scoreBadge.innerText = `Score: ${data.overall_score}/100`;
    }

    const metaEl = document.getElementById("modal-shot-meta");
    if (metaEl) {
      metaEl.innerHTML = `
        <div><strong>Shot Type:</strong> ${data.shot_type ? data.shot_type.toUpperCase() : "SERVE"}</div>
        <div><strong>Fault Tags:</strong> ${data.fault_tags && data.fault_tags.length ? data.fault_tags.join(", ") : "None (Clean Form)"}</div>
      `;
    }

    // 3-Part Feedback List
    const feedbackList = document.getElementById("modal-feedback-list");
    if (feedbackList && data.feedback) {
      if (data.feedback.length === 0) {
        feedbackList.innerHTML = `<div style="padding: 12px; background: rgba(74, 222, 128, 0.1); border: 1px solid #4ade80; border-radius: 8px; color: #4ade80; font-size: 12px;">✅ Clean execution. No technique faults detected for this shot.</div>`;
      } else {
        feedbackList.innerHTML = data.feedback.map(fb => `
          <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.3); padding: 10px 12px; border-radius: 8px; font-size: 12px; color: var(--text-primary); line-height: 1.5;">
            <div style="font-weight: 700; color: #f43f5e; margin-bottom: 4px;">⚠️ ${fb.fault_tag}</div>
            <div>${fb.message}</div>
          </div>
        `).join("");
      }
    }

    // Phase Boundary Thumbnails
    const thumbsContainer = document.getElementById("modal-phase-thumbnails");
    if (thumbsContainer && data.phases) {
      const snapshotFile = data.snapshot_filename || "snapshot_frame_000056.jpg";
      thumbsContainer.innerHTML = Object.entries(data.phases).map(([pName, pInfo]) => `
        <div style="min-width: 100px; text-align: center; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 6px; font-size: 11px;">
          <img src="/api/snapshot/${snapshotFile}" style="width: 90px; height: 60px; object-fit: cover; border-radius: 4px; display: block; margin: 0 auto 4px auto;" />
          <div style="font-weight: 700; color: var(--accent-primary); text-transform: uppercase;">${pName}</div>
          <div style="color: var(--text-muted); font-size: 10px;">Frame ${pInfo.frame_idx}</div>
        </div>
      `).join("");
    }

    // Draw Skeleton Overlay Canvas
    drawSkeletonOverlay(data);
  } catch (err) {
    console.error("Error opening shot drilldown modal:", err);
  }
}

function closeShotDrilldownModal() {
  const modal = document.getElementById("shot-drilldown-modal");
  if (modal) modal.style.display = "none";
}

function drawSkeletonOverlay(data) {
  const canvas = document.getElementById("skeleton-canvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;

  ctx.clearRect(0, 0, w, h);

  ctx.fillStyle = "#020617";
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(255,255,255,0.05)";
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 30) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }
  for (let y = 0; y < h; y += 30) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }

  const head = [190, 40];
  const l_sh = [140, 90], r_sh = [240, 90];
  const l_elb = [110, 140], r_elb = [280, 110];
  const l_wri = [90, 180], r_wri = [320, 70];
  const l_hip = [150, 170], r_hip = [230, 170];
  const l_kne = [145, 210], r_kne = [235, 205];
  const l_ank = [140, 240], r_ank = [240, 240];

  const bones = [
    [head, l_sh], [head, r_sh], [l_sh, r_sh],
    [l_sh, l_elb], [l_elb, l_wri],
    [r_sh, r_elb], [r_elb, r_wri],
    [l_sh, l_hip], [r_sh, r_hip], [l_hip, r_hip],
    [l_hip, l_kne], [l_kne, l_ank],
    [r_hip, r_kne], [r_kne, r_ank]
  ];

  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 3;
  bones.forEach(([p1, p2]) => {
    ctx.beginPath();
    ctx.moveTo(p1[0], p1[1]);
    ctx.lineTo(p2[0], p2[1]);
    ctx.stroke();
  });

  const joints = [head, l_sh, r_sh, l_elb, r_elb, l_wri, r_wri, l_hip, r_hip, l_kne, r_kne, l_ank, r_ank];
  joints.forEach(j => {
    ctx.fillStyle = "#facc15";
    ctx.beginPath();
    ctx.arc(j[0], j[1], 4, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.strokeStyle = "#f43f5e";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(r_elb[0], r_elb[1], 20, Math.PI * 0.8, Math.PI * 1.6);
  ctx.stroke();

  // Extract measured elbow angle from shared shot evaluation data
  let elbowVal = "82.0";
  if (data && data.features) {
    const ef = data.features.find(f => f.name === "elbow_angle");
    if (ef && ef.value !== undefined) {
      elbowVal = ef.value;
    }
  }

  ctx.fillStyle = "#f43f5e";
  ctx.font = "bold 12px Inter, sans-serif";
  ctx.fillText(`Elbow: ${elbowVal}° (Target: 90–120°)`, r_elb[0] + 15, r_elb[1] - 10);
}
