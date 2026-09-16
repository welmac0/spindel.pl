# Mac: automatyczne pobieranie backupow SQLite

Ten plik opisuje konfiguracje na osobnym Macu. Mac pobiera gotowe backupy z VPS przez SSH. Nie laczy sie z Dockerem i nie czyta bazy z wolumenu.

## Zalozenia

- VPS user: `spindel`
- VPS backup directory: `/opt/wymiana-zajec/backups`
- Mac local directory: `$HOME/wymiana-zajec-backups`
- SSH key on Mac: `$HOME/.ssh/id_ed25519_wymiana_vps`
- Replace `VPS_HOST` below with the VPS IPv4 (91.99.16.118) address or `spindel.pl`.
- Never put `.env`, Brevo keys, or private SSH keys in the repository.

## One-time Mac setup

Create the local directories:

```bash
mkdir -p "$HOME/bin" "$HOME/wymiana-zajec-backups"
chmod 700 "$HOME/wymiana-zajec-backups"
```

Test SSH first:

```bash
ssh -i "$HOME/.ssh/id_ed25519_wymiana_vps" spindel@91.99.16.118
```

Test read-only access to the backup directory:

```bash
ssh -i "$HOME/.ssh/id_ed25519_wymiana_vps" spindel@91.99.16.118 \
  'find /opt/wymiana-zajec/backups -maxdepth 1 -type f -name "database-*.db" -print'
```

## Backup download script

Create the script:

```bash
nano "$HOME/bin/pull-wymiana-backups.sh"
```

Paste this content and replace only `VPS_HOST`:

```bash
#!/bin/bash
set -Eeuo pipefail

VPS_USER="spindel"
VPS_HOST=91.99.16.118
SSH_KEY="$HOME/.ssh/id_ed25519_wymiana_vps"
REMOTE_DIR="/opt/wymiana-zajec/backups"
LOCAL_DIR="$HOME/wymiana-zajec-backups"
RETENTION_COUNT=14
LOCK_DIR="$LOCAL_DIR/.lock"

mkdir -p "$LOCAL_DIR"
chmod 700 "$LOCAL_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    printf 'Backup download is already running.\n' >&2
    exit 1
fi
trap 'rmdir "$LOCK_DIR"' EXIT

if [[ ! -r "$SSH_KEY" ]]; then
    printf 'SSH key is missing or unreadable: %s\n' "$SSH_KEY" >&2
    exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
    printf 'rsync is required.\n' >&2
    exit 1
fi

rsync -az --partial \
    -e "ssh -i $SSH_KEY -o BatchMode=yes" \
    "$VPS_USER@$VPS_HOST:$REMOTE_DIR/" \
    "$LOCAL_DIR/"

cd "$LOCAL_DIR"

for checksum_file in database-*.db.sha256; do
    [[ -e "$checksum_file" ]] || continue
    shasum -a 256 -c "$checksum_file"
done

backup_count=0
for backup_file in $(ls -1t database-*.db 2>/dev/null); do
    backup_count=$((backup_count + 1))
    if (( backup_count > RETENTION_COUNT )); then
        rm -f -- "$backup_file" "$backup_file.sha256"
    fi
done

printf 'Backup download and checksum verification completed.\n'
```

Make it executable:

```bash
chmod 700 "$HOME/bin/pull-wymiana-backups.sh"
```

Run the first manual test:

```bash
"$HOME/bin/pull-wymiana-backups.sh"
```

List downloaded files:

```bash
ls -lah "$HOME/wymiana-zajec-backups"
```

The script downloads only backup files and checksum files. It does not use `--delete`, so a local copy is not removed if a VPS file disappears.

## Automatic schedule with launchd

Create the LaunchAgent file:

```bash
mkdir -p "$HOME/Library/LaunchAgents"
nano "$HOME/Library/LaunchAgents/pl.spindel.backup.plist"
```

Paste this content and replace `YOUR_MAC_USERNAME` with the Mac username:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>pl.spindel.backup</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_MAC_USERNAME/bin/pull-wymiana-backups.sh</string>
    </array>

    <key>StartInterval</key>
    <integer>21600</integer>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/YOUR_MAC_USERNAME/Library/Logs/spindel-backup.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/YOUR_MAC_USERNAME/Library/Logs/spindel-backup-error.log</string>
</dict>
</plist>
```

Create the log directory:

```bash
mkdir -p "$HOME/Library/Logs"
```

Load the LaunchAgent:

```bash
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/pl.spindel.backup.plist"
```

Run it immediately once:

```bash
launchctl kickstart -k "gui/$(id -u)/pl.spindel.backup"
```

Check it:

```bash
launchctl print "gui/$(id -u)/pl.spindel.backup"
tail -n 50 "$HOME/Library/Logs/spindel-backup.log"
tail -n 50 "$HOME/Library/Logs/spindel-backup-error.log"
```

Unload it if necessary:

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/pl.spindel.backup.plist"
```

## What success means

A successful run means:

- `rsync` completed without an error,
- every downloaded `.sha256` file validates its matching `.db`,
- the local directory contains at most 14 database copies,
- the LaunchAgent is loaded and its log shows successful runs.

This is an additional copy outside the VPS. It does not replace the VPS timer, the Docker volume, or periodic restore testing.
