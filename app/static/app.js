// API helper
async function j(url, method = 'GET', body = null) {
  const options = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) options.body = JSON.stringify(body);
  const response = await fetch(url, options);
  return response.json();
}

// Format time helper
const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${String(secs).padStart(2, '0')}`;
};

// Update now playing section
function updateNowPlaying(nowData) {
  const nowElement = document.getElementById('now');
  
  if (!nowData) {
    nowElement.innerHTML = `
      <div class="now-content">
        <i>Nothing playing</i>
        <div class="controls" style="margin-top:16px">
          <button class="btn btn-primary" onclick="post('/play')">
            <span class="material-icons">play_arrow</span>
          </button>
          <button class="btn btn-secondary" onclick="post('/skip')">
            <span class="material-icons">skip_next</span>
          </button>
        </div>
      </div>
    `;
    return;
  }

  const pos = nowData.position || 0;
  const dur = nowData.duration || 0;
  const isPaused = nowData.paused || false;
  
  const playPauseBtn = isPaused ? 
    `<button class="btn btn-primary" onclick="post('/play')">
      <span class="material-icons">play_arrow</span>
    </button>` : 
    `<button class="btn btn-primary" onclick="post('/pause')">
      <span class="material-icons">pause</span>
    </button>`;

  nowElement.innerHTML = `
    <div class="now-content">
      <h2>${nowData.title}</h2>
      <div class="artist">${nowData.uploader}</div>
      <div class="progress-container">
        <span class="progress-time">${formatTime(pos)}</span>
        <input type="range" id="seek" min="0" max="${dur}" value="${pos}">
        <span class="progress-time">${formatTime(dur)}</span>
      </div>
      <div class="controls">
        ${playPauseBtn}
        <button class="btn btn-secondary" onclick="post('/skip')">
          <span class="material-icons">skip_next</span>
        </button>
      </div>
    </div>
  `;
  
  document.getElementById('seek').oninput = e => post('/seek', { pos: e.target.value });
}

// Update history display
function updateHistory(historyData) {
  const historyCard = document.getElementById('history-card');
  const historyList = document.getElementById('history-list');
  const historyCount = document.getElementById('history-count');
  
  if (!historyData || historyData.length === 0) {
    historyCard.style.display = 'none';
    return;
  }
  
  historyCard.style.display = 'block';
  historyList.innerHTML = '';
  historyCount.textContent = `${historyData.length} songs`;
  
  // Show history in reverse order (most recent first)
  historyData.slice().reverse().forEach((item, i) => {
    const div = document.createElement('div');
    div.className = 'queue-item';
    div.style.opacity = '0.8';
    
    const duration = item.duration ? formatTime(item.duration) : '';
    div.innerHTML = `
      <span class="material-icons queue-icon">history</span>
      <div class="queue-info">
        <div class="queue-title">${item.title}</div>
        <div class="queue-meta">${item.uploader} ${duration ? `• ${duration}` : ''}</div>
      </div>
      <button class="btn btn-secondary" onclick="replaySong('${item.id}')" style="padding:8px;min-width:auto">
        <span class="material-icons" style="font-size:16px">replay</span>
      </button>
    `;
    historyList.appendChild(div);
  });
}

// Update queue display
function updateQueue(queueData) {
  const listElement = document.getElementById('list');
  const queueCount = document.getElementById('queue-count');
  
  listElement.innerHTML = '';
  queueCount.textContent = `${(queueData || []).length} songs`;
  
  let autoplayStarted = false;
  (queueData || []).forEach((item, i) => {
    // Add separator before first autoplay song
    if (!autoplayStarted && item.added_by === 'autoplay') {
      const separator = document.createElement('div');
      separator.innerHTML = `
        <div style="text-align:center;padding:16px;color:var(--md-sys-color-on-surface-variant);font-size:14px;border-top:1px solid var(--md-sys-color-outline);margin:8px 0;">
          🎵 Auto-suggested songs
        </div>
      `;
      listElement.appendChild(separator);
      autoplayStarted = true;
    }
    
    const div = document.createElement('div');
    const isAutoplay = item.added_by === 'autoplay';
    const icon = isAutoplay ? 'queue_music' : 'person';
    const addedByText = isAutoplay ? 'Auto-suggested' : item.added_by || 'Anonymous';
    const duration = item.duration ? formatTime(item.duration) : '';
    
    div.className = `queue-item ${item.added_by === 'autoplay' ? 'autoplay' : ''}`;
    div.innerHTML = `
      <span class="material-icons queue-icon">${icon}</span>
      <div class="queue-info">
        <div class="queue-title">${item.title}</div>
        <div class="queue-meta">${item.uploader} ${duration ? `• ${duration}` : ''} • ${addedByText}</div>
      </div>
    `;
    listElement.appendChild(div);
  });
}

// Replay song from history
async function replaySong(songId) {
  // Find song in history and add it to queue
  const data = await j('/queue');
  const song = data.history.find(item => item.id === songId);
  if (song) {
    add(song.title + ' ' + song.uploader, false);
  }
}

// Main refresh function
async function refresh() {
  try {
    const data = await j('/queue');
    updateNowPlaying(data.now);
    updateHistory(data.history);
    updateQueue(data.queue);
  } catch (error) {
    console.error('Refresh failed:', error);
  }
}

// API post helper
async function post(url, body) {
  await j(url, 'POST', body);
  refresh();
}

// Add song function
async function add(query, playNext) {
  if (!query.trim()) return;
  
  // Get user info from localStorage
  const userInfo = JSON.parse(localStorage.getItem('jukeboxUser') || '{}');
  const addedBy = userInfo.alias ? `${userInfo.emoji} ${userInfo.alias}` : 'Anonymous';
  
  const allowAgeRestricted = document.getElementById('allowAgeRestricted').checked;
  try {
    const result = await j('/add', 'POST', {
      q: query,
      play_next: playNext,
      allow_age_restricted: allowAgeRestricted,
      by: addedBy
    });
    
    if (result.ok) {
      refresh();
    } else {
      alert('Error: ' + (result.error || 'unknown'));
    }
  } catch (error) {
    alert('Error: ' + error.message);
  }
}

// Settings toggle
function toggleSettings() {
  const settings = document.getElementById('settings');
  settings.style.display = settings.style.display === 'none' ? 'block' : 'none';
}

// QR code toggle
function toggleQR() {
  const qrPanel = document.getElementById('qr-panel');
  const qrCode = document.getElementById('qr-code');
  
  if (qrPanel.style.display === 'none') {
    // Generate QR code with Material 3 colors and rounded style
    const url = window.location.href;
    const primaryColor = '6750A4'; // Material 3 primary color without #
    const backgroundColor = 'FFFFFF';
    qrCode.innerHTML = `<img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(url)}&color=${primaryColor}&bgcolor=${backgroundColor}&qzone=2&format=svg" alt="QR Code" style="max-width:100%;border-radius:12px;background:white;padding:8px;">`;
    qrPanel.style.display = 'block';
  } else {
    qrPanel.style.display = 'none';
  }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
  refresh();
  setInterval(refresh, 2000);
});