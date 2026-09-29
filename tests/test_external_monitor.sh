#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MONITOR_SCRIPT="$REPO_ROOT/scripts/check_external_health.sh"
test_dir="$(mktemp -d)"
trap 'rm -rf -- "$test_dir"' EXIT

cat > "$test_dir/fake-curl" <<'FAKE_CURL'
#!/usr/bin/env bash
set -eu

url=""
payload=""
while (($#)); do
    case "$1" in
        --url|--data-binary|--max-time|--output|--request|--header)
            option="$1"
            value="$2"
            if [[ "$option" == "--url" ]]; then url="$value"; fi
            if [[ "$option" == "--data-binary" ]]; then payload="$value"; fi
            shift 2
            ;;
        --fail|--silent|--show-error|--location)
            shift
            ;;
        *)
            url="$1"
            shift
            ;;
    esac
done

if [[ "$url" == "https://api.brevo.com/v3/smtp/email" ]]; then
    printf '%s\n' "$payload" >> "$ALERT_LOG"
    exit 0
fi

[[ "${MOCK_HEALTH_STATUS:-up}" == "up" ]]
FAKE_CURL
chmod 700 "$test_dir/fake-curl"

export STATE_DIR="$test_dir/state"
export ALERT_LOG="$test_dir/alerts.jsonl"
export CURL_BIN="$test_dir/fake-curl"
export BREVO_API_KEY="test-key-not-a-real-secret"
export BREVO_SENDER_EMAIL="monitor@example.test"
export BREVO_SENDER_NAME="Monitor Test"
export ALERT_EMAIL="alerts@example.test"
export SPINDEL_HEALTH_URL="https://spindel.example.test/api/health"
export SPINDEL_NGINX_HEALTH_URL="https://spindel.example.test/nginx-health"
export MOCK_HEALTH_STATUS="down"

bash "$MONITOR_SCRIPT" >/dev/null
[[ "$(cat "$STATE_DIR/consecutive-failures")" == "1" ]]
[[ ! -f "$ALERT_LOG" ]]

bash "$MONITOR_SCRIPT" >/dev/null
[[ "$(cat "$STATE_DIR/status")" == "down" ]]
[[ "$(wc -l < "$ALERT_LOG" | tr -d ' ')" == "1" ]]

bash "$MONITOR_SCRIPT" >/dev/null
[[ "$(wc -l < "$ALERT_LOG" | tr -d ' ')" == "1" ]]
[[ "$(cat "$STATE_DIR/consecutive-failures")" == "2" ]]

export MOCK_HEALTH_STATUS="up"
bash "$MONITOR_SCRIPT" >/dev/null
[[ "$(cat "$STATE_DIR/status")" == "up" ]]
[[ "$(cat "$STATE_DIR/consecutive-failures")" == "0" ]]
[[ "$(wc -l < "$ALERT_LOG" | tr -d ' ')" == "2" ]]

printf 'External monitor transition tests passed.\n'