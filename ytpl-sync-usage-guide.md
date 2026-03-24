# ytpl-sync — Usage Guide

> A complete guide to installing, configuring, and running ytpl-sync on Linux, macOS, Windows, and Termux (Android).

---

## Prerequisites

### 1. Python 3.11+

**Linux/macOS:**
```bash
python3 --version   # check if already installed
```

**Termux (Android):**
```bash
pkg update && pkg install python
```

**Windows:**
Download from [python.org](https://python.org) — check "Add to PATH" during install.

---

### 2. ffmpeg

**Linux:**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Termux:**
```bash
pkg install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org) → extract → add the `bin` folder to your system PATH.

---

### 3. rclone

**Linux/macOS:**
```bash
curl https://rclone.org/install.sh | sudo bash
```

**Windows:**
Download the installer from [rclone.org](https://rclone.org/downloads/).

**Termux:**
```bash
pkg install rclone
```

---

### 4. Configure rclone for Google Drive

This is a one-time setup per Drive account. Run this for each account:

```bash
rclone config
```

Walk through the interactive prompts:
- Choose `n` for new remote
- Name it `gdrive1` (match exactly what you put in `config.yaml`)
- Choose `drive` as the storage type
- Leave client ID and secret blank (use defaults)
- Choose scope `drive` (full access)
- Open the auth URL in your browser, log in, paste the token back
- Say `No` to team drive

Repeat naming them `gdrive2`, `gdrive3` etc. for additional accounts.

**Verify it works:**
```bash
rclone lsd gdrive1:
```

---

## Installation

```bash
# 1. Clone or download the project
git clone https://github.com/souravagr8765/ytpl-sync.git
cd ytpl-sync

# 2. Create a virtual environment (recommended)
python3 -m venv .venv

# Activate it:
source .venv/bin/activate        # Linux / macOS / Termux
.venv\Scripts\activate           # Windows

# 3. Install the app
pip install -e .
```

---

## Configuration

### Step 1 — Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and fill in your secrets:

```env
NEON_DSN=postgres://user:password@host/dbname

GMAIL_SENDER=you@gmail.com
GMAIL_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx
GMAIL_RECIPIENT=you@gmail.com

TELEGRAM_BOT_TOKEN=123456789:AAxxxxxx
TELEGRAM_CHAT_ID=123456789
```

**Getting a Gmail App Password:**
1. Go to [myaccount.google.com](https://myaccount.google.com) → Security
2. Enable 2-Step Verification if not already on
3. Search "App Passwords" → create one named `ytpl-sync`
4. Copy the 16-character password into `.env`

**Getting Telegram credentials:**
1. Message `@BotFather` on Telegram → `/newbot` → follow prompts → copy the bot token
2. Message `@userinfobot` → it replies with your chat ID

---

### Step 2 — Create your `config.yaml`

Start from the example:

```bash
cp config.example.yaml config.yaml
```

Minimal working example:

```yaml
settings:
  min_free_gb: 3
  max_retries: 3
  ytdlp_auto_update: false
  dry_run: false

encoding:
  enabled: true
  encoder: software
  preset: medium
  crf: 28
  audio_bitrate: 96k

quality:
  max_resolution: 720
  prefer_format: webm

destination:
  mode: local
  local:
    path: ~/ytpl-downloads

notifications:
  email:
    enabled: true
    send_report_on_activity: true
    send_on_failure: true
  telegram:
    enabled: true
    send_report_on_activity: true
    send_on_failure: true

sources:
  - type: playlist
    name: "MIT Algorithms"
    url: "https://youtube.com/playlist?list=PLUl4u3cNGP63EdVPNLG3ToM6LaEUuStEY"
```

---

## Running the App

### Always do a dry run first

```bash
ytpl-sync --dry-run
```

This goes through the full flow — resolves videos, checks DB, prints exactly what it would download/encode/upload — but touches nothing. Verify the output looks right before a real run.

---

### Normal run

```bash
ytpl-sync
```

With a specific config file:

```bash
ytpl-sync --config /path/to/my-config.yaml
```

---

### Run only one specific source

Useful for testing a single playlist or channel without running all sources:

```bash
ytpl-sync --source "MIT Algorithms"
```

---

### Check version

```bash
ytpl-sync --version
```

---

## Automating with Cron / Termux Job Scheduler

### Linux / macOS — crontab

```bash
crontab -e
```

Add a line. Examples:

```bash
# Run every day at 3am
0 3 * * * /path/to/.venv/bin/ytpl-sync --config /path/to/config.yaml

# Run every 6 hours
0 */6 * * * /path/to/.venv/bin/ytpl-sync --config /path/to/config.yaml
```

Find your venv path:
```bash
which ytpl-sync   # run this after activating the venv
```

> **Important for cron:** cron doesn't load your shell environment, so use absolute paths everywhere — both in the cron line and in your `config.yaml` (avoid `~`, use `/home/yourname/...`).

Alternatively, use a small wrapper script:

```bash
#!/bin/bash
# ~/run-ytpl-sync.sh
source /home/yourname/ytpl-sync/.venv/bin/activate
cd /home/yourname/ytpl-sync
ytpl-sync --config config.yaml
```

```bash
chmod +x ~/run-ytpl-sync.sh

# Then in crontab:
0 3 * * * /home/yourname/run-ytpl-sync.sh
```

---

### Termux — cronie + Termux:Boot

Install the required addons:
- **Termux:Boot** from [F-Droid](https://f-droid.org) (not the Play Store)
- `pkg install cronie`

Start the cron daemon:
```bash
crond
```

Add to Termux crontab:
```bash
crontab -e

# Add (adjust paths as needed):
0 3 * * * /data/data/com.termux/files/usr/bin/python /data/data/com.termux/files/home/ytpl-sync/.venv/bin/ytpl-sync
```

Auto-start crond on phone boot via Termux:Boot:
```bash
mkdir -p ~/.termux/boot
nano ~/.termux/boot/start-crond.sh
```

```bash
#!/data/data/com.termux/files/usr/bin/bash
crond
```

```bash
chmod +x ~/.termux/boot/start-crond.sh
```

crond will now start automatically whenever Termux launches after a reboot.

---

### Windows — Task Scheduler

1. Open **Task Scheduler** → Create Basic Task
2. Name: `ytpl-sync`
3. Trigger: Daily at your preferred time
4. Action: Start a program
   - Program: `C:\path\to\ytpl-sync\.venv\Scripts\ytpl-sync.exe`
   - Start in: `C:\path\to\ytpl-sync\`
5. Finish

---

## Watching What It's Doing

### Live log output

```bash
# Linux / macOS / Termux
tail -f ~/.ytpl-sync.log

# Windows (PowerShell)
Get-Content $env:USERPROFILE\.ytpl-sync.log -Wait
```

---

### Inspect the database directly

```bash
# Install sqlite3 if needed:
# Linux:  sudo apt install sqlite3
# Termux: pkg install sqlite

sqlite3 ~/.ytpl-sync.db
```

Useful queries:

```sql
.mode column
.headers on

-- See everything downloaded and uploaded
SELECT title, status,
       original_size_bytes/1024/1024 AS orig_mb,
       final_size_bytes/1024/1024    AS final_mb,
       encoding_savings_pct
FROM videos
WHERE status = 'uploaded';

-- See failed videos
SELECT title, failed_stage, failed_reason, retry_count
FROM videos
WHERE status IN ('failed', 'abandoned');

-- See videos deleted from YouTube
SELECT title, deleted_detected_at
FROM videos
WHERE deleted = 1;

-- Count by status
SELECT status, COUNT(*)
FROM videos
GROUP BY status;

.quit
```

---

## Common Issues and Fixes

**"Another instance is already running"**
The lock file is stale — the script crashed without cleaning up. Delete it manually:
```bash
rm ~/.ytpl-sync.lock
```

**"yt-dlp: not found"**
```bash
pip install yt-dlp
# or update an existing install:
pip install --upgrade yt-dlp
```

**"ffmpeg: not found" on Termux**
```bash
pkg install ffmpeg
```

**rclone authentication expired**
Google Drive tokens can expire. Re-authenticate a remote:
```bash
rclone config reconnect gdrive1:
```

**Neon connection is slow on first run**
Neon's free tier suspends the database after inactivity. The first connection of the day takes a few seconds to wake up — this is normal. The reconciler has a connection timeout built in.

**Encoding is too slow on phone**
Disable encoding entirely, or use a faster preset:
```yaml
encoding:
  enabled: false

# OR keep it enabled but faster:
encoding:
  preset: ultrafast
  crf: 30
```

**Out of storage mid-run**
The script checks disk space at startup. Increase `min_free_gb` to give yourself more buffer, or reduce `max_resolution`:
```yaml
settings:
  min_free_gb: 5

quality:
  max_resolution: 480
```

---

## Config Recipes

### Phone (Termux) — fast, no encoding, local storage

```yaml
settings:
  min_free_gb: 2
  only_run_between: "01:00-05:00"   # run overnight only
  ytdlp_auto_update: true

encoding:
  enabled: false

quality:
  max_resolution: 480
  prefer_format: webm

destination:
  mode: local
  local:
    path: /storage/emulated/0/YT-Sync
```

---

### PC — full quality encode, upload to Google Drive

```yaml
encoding:
  enabled: true
  encoder: software        # change to nvenc for Nvidia GPU
  preset: slow
  crf: 26

quality:
  max_resolution: 1080

destination:
  mode: gdrive
  gdrive:
    accounts:
      - name: account-1
        rclone_remote: gdrive1
        quota_gb: 15
        upload_folder: Lectures
      - name: account-2
        rclone_remote: gdrive2
        quota_gb: 15
        upload_folder: Lectures
```

---

### Lecture channel with filters

```yaml
sources:
  - type: channel
    name: "MIT OpenCourseWare"
    url: "https://youtube.com/@mitocw"
    filters:
      after_date: "2022-01-01"
      min_duration_seconds: 600       # skip clips under 10 minutes
      exclude_keywords: ["trailer", "shorts", "promo"]
    encoding:
      crf: 30
      preset: fast
    quality:
      max_resolution: 720
```

---

### Mixed sources — different destinations per source

```yaml
destination:
  mode: gdrive                        # global default
  gdrive:
    accounts:
      - name: main-drive
        rclone_remote: gdrive1
        quota_gb: 15
        upload_folder: YT

sources:
  - type: playlist
    name: "Quick Reference"
    url: "https://youtube.com/playlist?list=..."
    destination:
      mode: local                     # override: save this one locally
      local:
        path: ~/lectures/quick-ref
    encoding:
      enabled: false

  - type: channel
    name: "3Blue1Brown"
    url: "https://youtube.com/@3blue1brown"
    # no destination override — uses global gdrive
    encoding:
      crf: 24
      preset: slow
```

---

## Quick Reference

| Command | What it does |
|---|---|
| `ytpl-sync` | Normal run using `./config.yaml` |
| `ytpl-sync --dry-run` | Simulate run, no downloads or uploads |
| `ytpl-sync --config path/to/config.yaml` | Use a specific config file |
| `ytpl-sync --source "Name"` | Run only the named source |
| `ytpl-sync --version` | Print version and exit |
| `tail -f ~/.ytpl-sync.log` | Watch live logs |
| `rm ~/.ytpl-sync.lock` | Remove stale lock file |
| `rclone config reconnect gdrive1:` | Re-authenticate a Drive account |
