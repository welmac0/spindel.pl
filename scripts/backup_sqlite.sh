#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
DATABASE_PATH="${DATABASE_PATH:-$PROJECT_DIR/database.db}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
RETENTION_COUNT="${RETENTION_COUNT:-14}"

if ! command -v sqlite3 >/dev/null 2>&1; then
    printf 'Error: sqlite3 is required but was not found in PATH.\n' >&2
    exit 1
fi

if ! command -v sha256sum >/dev/null 2>&1; then
    printf 'Error: sha256sum is required but was not found in PATH.\n' >&2
    exit 1
fi

if [[ ! -f "$DATABASE_PATH" ]]; then
    printf 'Error: database does not exist: %s\n' "$DATABASE_PATH" >&2
    exit 1
fi

if ! [[ "$RETENTION_COUNT" =~ ^[1-9][0-9]*$ ]]; then
    printf 'Error: RETENTION_COUNT must be a positive integer.\n' >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%d-%H%M%S)"
final_path="$BACKUP_DIR/database-$timestamp.db"
temporary_path="$BACKUP_DIR/.database-$timestamp.db.tmp"
checksum_path="$final_path.sha256"

cleanup() {
    rm -f -- "$temporary_path"
}
trap cleanup EXIT

on_error() {
    printf 'Backup failed.\n' >&2
    exit 1
}
trap on_error ERR

sqlite3 "$DATABASE_PATH" ".backup '$temporary_path'"

integrity_result="$(sqlite3 "$temporary_path" 'PRAGMA integrity_check;')"
if [[ "$integrity_result" != "ok" ]]; then
    printf 'Error: SQLite integrity check failed: %s\n' "$integrity_result" >&2
    exit 1
fi

mv -- "$temporary_path" "$final_path"
sha256sum "$final_path" > "$checksum_path"

if sha256sum --check "$checksum_path" >/dev/null; then
    :
else
    printf 'Checksum FAILED: %s\n' "$final_path" >&2
    exit 1
fi

mapfile -t old_backups < <(
    find "$BACKUP_DIR" -maxdepth 1 -type f -name 'database-*.db' -printf '%T@ %p\n' |
        sort -nr |
        tail -n +$((RETENTION_COUNT + 1)) |
        cut -d' ' -f2-
)

for old_backup in "${old_backups[@]}"; do
    rm -f -- "$old_backup" "$old_backup.sha256"
done

printf 'Backup created [OK]: %s\n' "$final_path"
printf 'Checksum: %s\n' "$checksum_path"
exit 0