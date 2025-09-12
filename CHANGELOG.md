# Changelog

All notable changes to Wi-Fi Jukebox will be documented in this file.

## [1.0.0] - 2025-09-12

### Added
- **Last.fm Integration**: Smart music recommendations based on listening history
- **Session Detection**: Auto-suggestions only during active sessions (3-hour window)
- **Dual Queue Options**: "Play Next" (priority) vs "Add to Queue" (normal)
- **Visual Queue Separation**: Icons distinguish user-added (👤) vs auto-suggested (🎵) songs
- **Duration Display**: Shows song length (MM:SS) for all queued tracks
- **Smart Music Filtering**: Prefers music content (30sec-20min), avoids podcasts/tutorials
- **Duplicate Prevention**: Tracks suggested songs to avoid repeats
- **Organized File Structure**: `Artist/Year Album/` hierarchy with metadata folders
- **Rich Metadata**: Extracts artist, album, year, thumbnails from YouTube
- **Makefile**: Development commands for build, format, lint, and run
- **Environment Variables**: Support for Last.fm API keys via `.env` file

### Changed
- **File Organization**: Music now organized in structured folders instead of flat directory
- **Auto-suggestions**: Replaced random suggestions with intelligent Last.fm recommendations
- **Search Results**: Now fetches 10 results and filters for best music match
- **Duration Limits**: Allows songs up to 20 minutes (for prog rock, Pink Floyd, etc.)

### Technical
- **Dependencies**: Added `requests` for Last.fm API, `ruff` for code formatting
- **Code Quality**: All imports moved to top-level, proper error handling
- **Docker**: Improved container setup with proper dependency management
- **Database**: Enhanced schema for better metadata tracking

## [0.0.1] - Initial Release

### Added
- Basic YouTube URL and search functionality
- Shared queue with real-time updates
- Playback controls (play, pause, skip, seek)
- Auto-download to local storage
- SQLite database for tracking downloads
- Web interface for mobile devices
- Docker support for development
- Termux scripts for Android deployment