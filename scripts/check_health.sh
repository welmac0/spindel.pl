#!/usr/bin/env bash
set -Eeuo pipefail

HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"
STATE_FILE="${STATE_FILE:-/run/wymiana-zajec-health/status}"

required_variables=(
    BREVO_API_KEY
    BREVO_SENDER_EMAIL
    BREVO_SENDER_NAME
    ALERT_EMAIL
)

for variable_name in "${required_variables[@]}"; do
    if [[ -z "${!variable_name:-}" ]]; then
        printf 'Error: %s is not set.\n' "$variable_name" >&2
        exit 1
    fi
done

mkdir -p "$(dirname -- "$STATE_FILE")"
previous_status="$(cat "$STATE_FILE" 2>/dev/null || printf 'unknown')"

if curl --fail --silent --show-error --max-time 10 "$HEALTH_URL" >/dev/null; then
    current_status="up"
else
    current_status="down"
fi

send_alert() {
    local subject="$1"
    local text_content="$2"

    curl --fail --silent --show-error --max-time 20 \
        --request POST \
        --url "https://api.brevo.com/v3/smtp/email" \
        --header "accept: application/json" \
        --header "api-key: $BREVO_API_KEY" \
        --header "content-type: application/json" \
        --data-binary @- <<EOF
{"sender":{"name":"$BREVO_SENDER_NAME","email":"$BREVO_SENDER_EMAIL"},"to":[{"email":"$ALERT_EMAIL"}],"subject":"$subject","textContent":"$text_content"}
EOF
}

if [[ "$current_status" == "down" && "$previous_status" != "down" ]]; then
    send_alert \
        "Wymiana Grup PW: backend niedostepny" \
        "Health check nie otrzymal poprawnej odpowiedzi z $HEALTH_URL. Sprawdz status uslugi systemd i journalctl."
    printf 'down\n' > "$STATE_FILE"
elif [[ "$current_status" == "up" && "$previous_status" == "down" ]]; then
    send_alert \
        "Wymiana Grup PW: backend przywrocony" \
        "Health check ponownie otrzymuje poprawna odpowiedz z $HEALTH_URL."
    printf 'up\n' > "$STATE_FILE"
elif [[ "$previous_status" == "unknown" ]]; then
    printf '%s\n' "$current_status" > "$STATE_FILE"
fi

if [[ "$current_status" == "up" ]]; then
    exit 0
fi

exit 1