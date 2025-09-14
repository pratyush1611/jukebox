# Wi-Fi Jukebox v2.0.0

A web-based music player that runs on Android (via Termux) and lets people on the same Wi-Fi network add YouTube videos to a shared queue. Music plays through the Android phone's speakers.

## Features

### Core Features
- **YouTube Integration**: Add songs via YouTube URL or search
- **Shared Queue**: Real-time queue visible to all users on Wi-Fi network
- **Smart Playback Controls**: Play, pause, skip, seek with progress bar
- **Dual Add Options**: "Play Next" (priority) or "Add to Queue" (normal)
- **Auto-Downloads**: Organized music library in `~/storage/Music/Artist/Year Album/`
- **Rich Metadata**: Extracts artist, album, year, thumbnails from YouTube
- **SQLite Database**: Tracks all downloaded songs with metadata

### Intelligent Auto-Suggestions
- **Last.fm Integration**: Uses Last.fm API for music recommendations
- **Session-Aware**: Only suggests music during active listening sessions (3-hour window)
- **Smart Filtering**: Prefers music content (30sec-20min), avoids podcasts/tutorials
- **Duplicate Prevention**: Tracks suggested songs to avoid repeats
- **3-Hour Session History**: Prevents suggesting songs already played in current session
- **Age-Restriction Control**: User-configurable filtering of age-restricted content
- **Cookie Authentication**: Supports YouTube cookies for accessing restricted content
- **Personalized**: Based on your actual listening history

### User Interface
- **Material 3 Design**: Modern mobile-first UI with proper color schemes and typography
- **User Landing Page**: Name/emoji selection for personalized queue tracking
- **Session History**: Recently played songs with replay functionality (last 20 tracks)
- **QR Code Sharing**: Material 3 styled QR codes for easy device connection
- **User Identity Tracking**: Queue shows who added each song with emoji + name
- **Visual Queue Separation**: Icons distinguish user-added vs auto-suggested songs
- **Smart Playbook Controls**: Context-aware play/pause button (shows only relevant action)
- **Integrated Controls**: Play/pause/skip buttons positioned under progress slider
- **Age-Restriction Toggle**: Collapsible settings panel with content filtering
- **Real-time Updates**: Queue refreshes every 2 seconds
- **Mobile-Optimized**: Touch-friendly controls with proper spacing
- **Progress Tracking**: Shows current song position and duration

## Quick Start

### On Android (Termux)

```bash
# Clone and setup
git clone <repo-url>
cd jukebox
make all  # Formats code, builds, and runs
# OR manually:
bash scripts/setup_termux.sh
bash scripts/setup_boot.sh  # Optional: auto-start on boot
bash scripts/start_termux.sh
```

### Local Development (Docker)

```bash
# Quick start
make local

# Development with live logs
make dev

# Other commands
make build    # Build Docker image
make logs     # View logs
make format   # Format code with ruff
make lint     # Lint code with ruff
make clean    # Remove containers and cleanup
```

Open http://localhost:5000 in your browser.

**Network Access:**
- **Docker**: Auto-detects host IP or set `HOST_IP` environment variable
- **QR Code**: Click QR icon in app to generate shareable QR code
- **Share URL**: Use the network IP shown in startup logs for other devices

**User Flow:**
1. **Landing Page**: Enter name and choose emoji for identity
2. **Main App**: Add songs, view queue, and see who added what
3. **History**: Replay recently played songs from session history

## Configuration

### Environment Variables

- `PORT`: Server port (default: 5000)
- `MPV_IPC`: MPV socket path (default: /tmp/mpv.sock)
- `MPV_EXTRA`: Additional MPV arguments
- `LASTFM_API_KEY`: Last.fm API key for music recommendations
- `LASTFM_SHARED_SECRET`: Last.fm shared secret

### Last.fm Setup (Optional)

1. Get API key from https://www.last.fm/api/account/create
2. Add to `.env` file:
```
LASTFM_API_KEY=your_api_key_here
LASTFM_SHARED_SECRET=your_secret_here
```

## File Organization

**Code Structure:**
```
app/
├── jukebox.py          # Python backend
├── landing.html        # User onboarding page
├── jukebox.html        # Main app interface
└── static/
    ├── styles.css      # Material 3 design system
    ├── landing.css     # Landing page styles
    └── app.js         # Frontend functionality
```

**Music Storage:**
```
~/storage/music/        # Android Music folder (Termux)
├── Artist Name/
│   ├── 2023 Album Name/
│   │   ├── Artist Name - Song Title.m4a
│   │   └── metadata/
│   │       ├── Artist Name - Song Title.info.json
│   │       └── Artist Name - Song Title.jpg
```

## Requirements

- Python 3.12+
- mpv player
- ffmpeg
- uv (Python package manager)
- Docker (for local development)