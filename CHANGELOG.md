# Changelog

All notable changes to Wi-Fi Jukebox will be documented in this file.

## [2.0.0] - 2024-09-13

### BREAKING CHANGES
- **Route Changes**: Main app moved from `/` to `/app` (landing page now at `/`)
- **User Flow**: Landing page with name/emoji selection now required
- **File Structure**: Modular architecture with separate CSS/JS files

### Added
- **User Landing Page**: Beautiful Material 3 onboarding with name/emoji selection
- **Session History**: Track and replay last 20 played songs with dedicated history section
- **QR Code Sharing**: Generate Material 3 styled QR codes for easy device connection
- **User Identity Tracking**: Queue displays who added each song with emoji + name
- **Modular Architecture**: Separated HTML, CSS, and JS files for better maintainability

### Changed
- **Complete UI Overhaul**: Migrated to Material 3 design system with mobile-first approach
- **Improved Code Organization**: Split monolithic HTML into modular components
- **Enhanced Mobile Experience**: Touch-friendly controls with proper spacing and typography
- **Better User Flow**: Landing page → main app → history tracking workflow

### Technical
- Added static file serving for CSS/JS assets
- Implemented localStorage for user session persistence  
- Added history API endpoint with replay functionality
- Enhanced queue display with user attribution
- Improved QR code generation with custom styling

## [1.0.1] - 2024-09-12

### Added
- **Smart Playback Controls**: Context-aware play/pause button (shows only relevant action)
- **Integrated Control Layout**: Play/pause/skip buttons positioned under progress slider
- **Age-Restriction Toggle**: UI checkbox to allow/block age-restricted YouTube content
- **Cookie Authentication**: Support for YouTube cookies to access restricted content
- **Network IP Display**: Automatic detection and display of shareable network URL

### Fixed
- **Android Audio Support**: Added OpenSL ES and ALSA audio output for Termux compatibility
- **Termux Path Detection**: Auto-detects Android vs Docker environment for correct paths
- **Music Directory Fix**: Uses correct Android Music symlink for file manager visibility
- **Play/Pause Responsiveness**: Proper mpv pause state detection for accurate UI buttons
- **Socket Connection Issues**: Fixed mpv IPC communication on Termux

### Changed
- **Optimized Resolution**: Reduced YouTube search results (10→3) for faster mobile performance
- **Better Loading Feedback**: "Searching YouTube..." placeholder with progress indication
- **Enhanced Error Logging**: Detailed tracebacks for debugging resolution failures

## [1.0.0] - 2024-09-11

### Added
- **Core Jukebox Functionality**: YouTube integration with shared queue system
- **Smart Playback Controls**: Play, pause, skip with progress bar and seeking
- **Dual Add Options**: "Play Next" (priority) vs "Add to Queue" (normal)
- **Auto-Downloads**: Organized music library with metadata extraction
- **Last.fm Integration**: Intelligent auto-suggestions based on listening history
- **SQLite Database**: Track downloaded songs with rich metadata
- **Termux Support**: Complete Android setup with audio routing
- **Docker Development**: Local development environment with live reload
- **Mobile-Responsive UI**: Basic responsive design for phones/tablets

### Technical
- Flask backend with mpv integration
- yt-dlp for YouTube content extraction
- Real-time queue updates every 2 seconds
- Session-aware auto-suggestions (3-hour window)
- Organized file structure with artist/album hierarchy