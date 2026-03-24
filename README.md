# ytpl-sync

Download YouTube playlists and channels, encode them efficiently, and back them up to Google Drive or local storage. Tracks everything in a database with Gmail and Telegram notifications.

## Requirements

- Python 3.11+
- ffmpeg
- rclone (only if using Google Drive)

Install Python dependencies:
  pip install -r requirements.txt

## Setup

1. Copy and fill in your config:
   - Edit `config.yaml` (created automatically on first run)
   - Edit `.env` (created automatically on first run)

2. If using Google Drive, set up rclone once:
   rclone config
   (name your remotes gdrive1, gdrive2 etc. to match config.yaml)

## Run

  python main.py

Dry run (simulate without downloading anything):
  python main.py --dry-run

Run only one source:
  python main.py --source "Source Name"

## Logs

Logs are written to the path set in config.yaml under settings.log_file (default: ~/.ytpl-sync.log).

Watch live:
  tail -f ~/.ytpl-sync.log        (Linux/macOS/Termux)
  Get-Content ~\.ytpl-sync.log -Wait   (Windows PowerShell)

## Automating

Use cron (Linux/macOS/Termux) or Task Scheduler (Windows) to run `python main.py` on a schedule.
