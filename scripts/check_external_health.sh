#!/usr/bin/env bash
set -Eeuo pipefail

# External Spindel monitor. Run this on a machine outside the VPS (for example,
# a Raspberry Pi at home). It checks public HTTPS endpoints and sends an email
# only on a down/recovery transition; it does not need SSH or access to the VPS.
#
# Ubuntu setup steps are documented in docs/operations.md, section
# "Niezalezny monitoring z Raspberry Pi". In short:
#   1. Install curl and python3, create a dedicated system user.
#   2. Copy this script to /usr/local/sbin/spindel-external-monitor.sh.
#   3. Install the matching systemd service and timer from deployment/systemd/.
#   4. Create /etc/spindel-monitor/monitor.env (root-owned, mode 0640) with
#      BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME and ALERT_EMAIL.
#   5. Enable the timer and verify its journal and a deliberate test outage.
#
# Do not put API keys in this script or commit the monitor.env file.

STATE_DIR="${STATE_DIR:-/var/lib/spindel-external-monitor}"
FAILURE_THRESHOLD="${FAILURE_THRESHOLD:-2}"
CURL_BIN="${CURL_BIN:-curl}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

HEALTH_URLS=(
    "${SPINDEL_HEALTH_URL:-https://spindel.pl/api/health}"
    "${SPINDEL_NGINX_HEALTH_URL:-https://spindel.pl/nginx-health}"
)

required_variables=(BREVO_API_KEY BREVO_SENDER_EMAIL BREVO_SENDER_NAME ALERT_EMAIL)
for variable_name in "${required_variables[@]}"; do
    if [[ -z "${!variable_name:-}" ]]; then
        printf 'Error: %s is not set. Configure it in monitor.env.\n' "$variable_name" >&2
        exit 2
    fi
done

for executable in "$CURL_BIN" "$PYTHON_BIN"; do
    if ! command -v "$executable" >/dev/null 2>&1; then
        printf 'Error: required executable not found: %s\n' "$executable" >&2
        exit 2
    fi
done

if ! [[ "$FAILURE_THRESHOLD" =~ ^[1-9][0-9]*$ ]]; then
    printf 'Error: FAILURE_THRESHOLD must be a positive integer.\n' >&2
    exit 2
fi

mkdir -p "$STATE_DIR"
status_file="$STATE_DIR/status"
failure_file="$STATE_DIR/consecutive-failures"
previous_status="$(cat "$status_file" 2>/dev/null || printf 'up')"
failure_count="$(cat "$failure_file" 2>/dev/null || printf '0')"
if ! [[ "$failure_count" =~ ^[0-9]+$ ]]; then
    failure_count=0
fi

failed_urls=()
for health_url in "${HEALTH_URLS[@]}"; do
    if ! "$CURL_BIN" \
        --fail \
        --silent \
        --show-error \
        --location \
        --max-time 15 \
        --output /dev/null \
        "$health_url" 2>/dev/null; then
        failed_urls+=("$health_url")
    fi
done

write_state() {
    local path="$1"
    local value="$2"
    local temporary_path="${path}.tmp"
    printf '%s\n' "$value" > "$temporary_path"
    mv -- "$temporary_path" "$path"
}

send_alert() {
    local subject="$1"
    local body="$2"
    local payload

    payload="$(
        ALERT_SENDER_NAME="$BREVO_SENDER_NAME" \
        ALERT_SENDER_EMAIL="$BREVO_SENDER_EMAIL" \
        ALERT_EMAIL="$ALERT_EMAIL" \
        ALERT_SUBJECT="$subject" \
        ALERT_TEXT="$body" \
        "$PYTHON_BIN" -c 'import json, os; print(json.dumps({"sender": {"name": os.environ["ALERT_SENDER_NAME"], "email": os.environ["ALERT_SENDER_EMAIL"]}, "to": [{"email": os.environ["ALERT_EMAIL"]}], "subject": os.environ["ALERT_SUBJECT"], "textContent": os.environ["ALERT_TEXT"]}, ensure_ascii=False))'
    )" || {
        printf 'Error: could not encode alert JSON.\n' >&2
        return 1
    }

    "$CURL_BIN" \
        --fail \
        --silent \
        --show-error \
        --max-time 20 \
        --request POST \
        --url "https://api.brevo.com/v3/smtp/email" \
        --header "accept: application/json" \
        --header "api-key: $BREVO_API_KEY" \
        --header "content-type: application/json" \
        --data-binary "$payload" >/dev/null
}

if ((${#failed_urls[@]} > 0)); then
    if ((failure_count < FAILURE_THRESHOLD)); then
        failure_count=$((failure_count + 1))
    fi
    write_state "$failure_file" "$failure_count"

    if ((failure_count >= FAILURE_THRESHOLD)) && [[ "$previous_status" != "down" ]]; then
        failed_list="$(printf '%s\n' "${failed_urls[@]}")"
        alert_body="$(printf 'Co najmniej %s kolejnych kontroli z Raspberry Pi nie uzyskalo poprawnej odpowiedzi HTTP z:\n%s\nSprawdz produkcyjne kontenery i logi na VPS.' \
            "$FAILURE_THRESHOLD" "$failed_list")"
        send_alert \
            "Spindel: niedostepnosc produkcji" \
            "$alert_body"
        write_state "$status_file" "down"
        printf 'Production is down; alert sent after %s consecutive failed checks.\n' "$failure_count"
    elif [[ "$previous_status" == "down" ]]; then
        printf 'Production remains down; alert already sent.\n'
    else
        printf 'Failed external check (%s/%s consecutive failures); waiting before alert.\n' \
            "$failure_count" "$FAILURE_THRESHOLD"
    fi

    exit 0
fi

write_state "$failure_file" "0"
if [[ "$previous_status" == "down" ]]; then
    send_alert \
        "Spindel: produkcja przywrocona" \
        "Publiczne endpointy https://spindel.pl/api/health i https://spindel.pl/nginx-health ponownie odpowiadaja poprawnie z zewnetrznego monitora."
    printf 'Production recovered; recovery alert sent.\n'
else
    write_state "$status_file" "up"
fi