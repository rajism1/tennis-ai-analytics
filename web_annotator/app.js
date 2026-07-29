// Tennis AI - Event Labeling & Accuracy Verification Client Script

let eventsData = [];
let selectedEventIndex = -1;
const video = document.getElementById("match-video");
const FPS = 59.0; // Raw video FPS

document.addEventListener("DOMContentLoaded", () => {
  loadEvents();
  setupEventListeners();
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
  const vTableMode = document.getElementById("video-table-mode");
  const vGalleryMode = document.getElementById("gallery-mode");

  vTableBtn.addEventListener("click", () => {
    vTableMode.style.display = "grid";
    vGalleryMode.style.display = "none";
    vTableBtn.classList.add("btn-primary");
    vGalleryBtn.classList.remove("btn-primary");
  });

  vGalleryBtn.addEventListener("click", () => {
    vTableMode.style.display = "none";
    vGalleryMode.style.display = "block";
    vGalleryBtn.classList.add("btn-primary");
    vTableBtn.classList.remove("btn-primary");
    renderGallery();
  });

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

// Export Verified CSV
function exportVerifiedCSV() {
  window.open("/api/export_csv", "_blank");
}
