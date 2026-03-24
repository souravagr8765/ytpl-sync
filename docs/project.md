# ytpl-sync Project Documentation

## Project Overview
`ytpl-sync` is a robust Python 3.11+ application that synchronizes YouTube playlists and channels to local storage and optionally to Google Drive. It handles downloading, optional video encoding, state management with persistent databases, custom retry logic, and notifications on activity or failure.

## System Architecture
The application is structured into a main package `ytpl_sync` with highly cohesive subpackages:
- **`config.py` & `models.py`**: Pydantic definitions and dataclasses/enums for state and validation.
- **`sources/`**: Resolves and parses YouTube items from predefined playlists or channels.
- **`db/`**: Handles local SQLite tracking and remote Neon PostgreSQL reconciliation.
- **`downloader.py` & `encoder.py`**: Dedicated modules for running `yt-dlp` and `ffmpeg`.
- **`storage/`**: Routes finalized video files to their local or GDrive destinations.
- **`notifications/`**: Manages email (Gmail) and Telegram alert pipelines.

## Database Schema
The primary entity is a **Video** with the following state tracking:
- **Identifier**: `video_id`, `source_name`, `source_url`, `run_id`
- **YouTube Metadata**: `title`, `description`, `upload_date`, `duration_seconds`, etc.
- **Status Enum**: `PENDING`, `DOWNLOADING`, `DOWNLOADED`, `ENCODING`, `ENCODED`, `UPLOADING`, `UPLOADED`, `FAILED`, `ABANDONED`, `DELETED`
- **Deletion Tracking**: Boolean `deleted` flag and `deleted_detected_at` timestamp
- **File & Paths**: Configurable save locations (Local/Temp/Rclone)
- **Timestamps**: Highly detailed step-by-step history

## Environment Configuration
The `.env` file must supply credentials that are excluded from source control.
Structure expectations (`.env` keys):
- **Database**: `NEON_DSN`
- **Gmail Notifications**: `GMAIL_SENDER`, `GMAIL_APP_PASSWORD`, `GMAIL_RECIPIENT`
- **Telegram Annotations**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Configuration Management
Configurations are stored in `config.yaml` and mapped into `ytpl_sync.config`.
Settings can be defined globally and optionally overridden per-source. All path accesses (e.g., `~/.ytpl-sync.lock`) automatically undergo tilde expansion (`Path.expanduser()`).

## Code Workflow
1. **Startup**: Entry point `ytpl-sync` starts the run. Reads `config.yaml` and `.env`.
2. **Context Setup**: Initialize `RunContext` to track metrics. Acquire application lock (`lock.py`).
3. **Database Reconcile**: Sync local state with remote Neon backend.
4. **Resolution**: Iterate `config.sources`. Fetch definitions by querying `yt-dlp`. Compare against DB.
5. **Download Pipeline**: Stream unresolved PENDING videos through `yt-dlp` to temp folder.
6. **Encode Pipeline**: Optionally run video chunks through `ffmpeg` (e.g. nvenc, software).
7. **Storage Router**: Move finished data to local and optionally GDrive (via `rclone`).
8. **Feedback Loop**: Report state matrix updates back to DB. Send `notifications/`. 
9. **Finalize**: Generate run summary and release lock.
