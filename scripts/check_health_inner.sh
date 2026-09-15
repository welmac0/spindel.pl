#!/usr/bin/env bash
set -Eeuo pipefail

# na maszynie host jest docker engine, on odpala kontenery jako 
# podprocesy glownego systemu, ale przez to ze skrypt uzywa docker inspect to 
# check_health_inner bedzie dzialal bezproblemowo i nie uzywa portow

# Host-side monitor for the Docker Compose backend health status.
COMPOSE_FILE="${COMPOSE_FILE:-/opt/wymiana-zajec/docker/compose.prod.yaml}"
SERVICE_NAME="${SERVICE_NAME:-backend}"
STATE_FILE="${STATE_FILE:-/run/wymiana-zajec-health/docker-status}"

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

if ! command -v docker >/dev/null 2>&1; then
    printf 'Error: docker is required but was not found in PATH.\n' >&2
    exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
    printf 'Error: curl is required but was not found in PATH.\n' >&2
    exit 1
fi

mkdir -p "$(dirname -- "$STATE_FILE")"
previous_status="$(cat "$STATE_FILE" 2>/dev/null || printf 'unknown')"

container_id=""
if [[ -f "$COMPOSE_FILE" ]]; then
    container_id="$(docker compose -f "$COMPOSE_FILE" ps -q "$SERVICE_NAME" 2>/dev/null || true)"
fi

current_status="down"
if [[ -n "$container_id" ]]; then
    health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$container_id" 2>/dev/null || printf 'inspect-failed')"
    if [[ "$health_status" == "healthy" ]]; then
        current_status="up"
    fi
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
        "Wymiana Grup PW: Docker backend niedostepny" \
        "Docker backend '$SERVICE_NAME' nie ma statusu healthy. Sprawdz: docker compose -f $COMPOSE_FILE ps oraz docker compose -f $COMPOSE_FILE logs $SERVICE_NAME."
    printf 'down\n' > "$STATE_FILE"
elif [[ "$current_status" == "up" && "$previous_status" == "down" ]]; then
    send_alert \
        "Wymiana Grup PW: Docker backend przywrocony" \
        "Docker backend '$SERVICE_NAME' ponownie ma status healthy."
    printf 'up\n' > "$STATE_FILE"
elif [[ "$previous_status" == "unknown" ]]; then
    printf '%s\n' "$current_status" > "$STATE_FILE"
fi

if [[ "$current_status" == "up" ]]; then
    exit 0
fi

exit 1
