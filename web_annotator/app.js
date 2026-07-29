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
  document.getElementById("filter-player").addEventListener("change", renderTable);
  document.getElementById("filter-status").addEventListener("change", renderTable);
  document.getElementById("search-input").addEventListener("input", renderTable);

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

// Select Event Row & Jump Video
function selectEvent(idx) {
  if (idx < 0 || idx >= eventsData.length) return;
  selectedEventIndex = idx;

  const evt = eventsData[idx];
  
  // Seek video to frame_idx
  const frame = evt.frame_idx || 0;
  video.currentTime = frame / FPS;
  video.pause();

  // Populate Edit Form
  document.getElementById("edit-player").value = evt.player || "Player 1";
  document.getElementById("edit-event-type").value = evt.event_type || "Hit";
  document.getElementById("edit-stroke").value = evt.stroke || "Forehand";
  document.getElementById("edit-spin").value = evt.spin || "Topspin";
  document.getElementById("edit-result").value = evt.result || "In Play";

  // Update Video Overlay Badge
  document.getElementById("overlay-event-text").innerText = `${evt.player} - ${evt.event_type} (${evt.stroke})`;

  renderTable();
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
