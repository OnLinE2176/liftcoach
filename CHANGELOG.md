# Changelog

All notable changes to the LiftCoach AI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adhers to semantic or chronological versioning.

## [2026-03-10]

### Added
- Implement a live recording finished state to hide the webcam stream and show a success message with a restart option after analysis.
- Implement live session recording and analysis within the real-time practice mode.
- Add cached function to provide multiple STUN servers for improved WebRTC configuration.
- Replace live recording with real-time MediaPipe pose detection and visualization using `streamlit_webrtc`.
- Add `ffmpeg` to `Dockerfile` for multimedia processing.
- Implement initial data persistence for LiftCoach AI.
- Display analyzed videos from Cloudflare R2 with fallback to local files and direct download links.
- Add script to seed Supabase with dummy user and analysis session data for demonstration.
- Add Nixpacks configuration for the Streamlit app, defining system dependencies and the start command.

### Changed
- Update `streamlit-webrtc` integration to use `VideoProcessorBase` instead of `VideoTransformerBase`.
- Update README to specify Olympic weightlifting analysis with IWF standards for Snatch and Clean & Jerk.
- Streamline README to focus on MediaPipe implementation, remove YOLOv8 details, and add environment variable setup instructions.
- Use `storage.get_video_url` to fetch video paths, supporting both local files and remote URLs for display.
- Update storage logic in `storage.py`.
- Update video codec from `avc1` to `mp4v` for output video files.
- Add Dockerfile for application containerization and configure Railway to use it for deployment.
- Add Supabase ERD and table schema diagrams, and update package dependencies.
- Refine kinematic data formatting for bar speed and depth.
- Remove emojis from log messages.

### Fixed
- Retrieve video URL using `video_filename` key with safe `.get()` access instead of direct `video_path` access.
- Explicitly cast `created_at` to string before slicing for display in UI.
- Correct typo in early exit statement in `seed_supabase.py`.

## [2026-03-09]

### Added
- Add Railway deployment configuration and ignore `.env` file.
- Introduce a Super Admin panel for user role management, global system configuration, audit logging, and cloud storage integration.
- Add `runtime.txt` to specify Python 3.11.
- Add `pose_landmarker_lite.task`, remove `*.task` from `.gitignore`, and update `requirements.txt`.

### Changed
- Update `libglib2.0-0` dependency to `libglib2.0-0t64`.
- Add `libglib2.0-0` to required packages.
- Add `.python-version` file specifying Python 3.11.
- Replace `libgl1-mesa-glx` with `libgl1` in `packages.txt`.

## [2026-03-05]

### Added
- Initial project creation: LiftCoach AI project.
