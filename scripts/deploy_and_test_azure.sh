#!/usr/bin/env bash
set -euo pipefail

# Configuration via env vars
: "${GIT_REMOTE:=origin}"
: "${GIT_BRANCH:=main}"
: "${WAIT_SECS:=60}"
: "${AZURE_RESOURCE_GROUP:=}"
: "${SERVER_URL:=}"
: "${DB_SERVER_API_KEY:=}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
CLIENT_DIR="$ROOT_DIR/app/client"

pushd "$ROOT_DIR" >/dev/null

echo "[+] Git add/commit/push to ${GIT_REMOTE} ${GIT_BRANCH}"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[-] Not a git repo. Aborting." >&2
  exit 1
fi

git add -A
if ! git diff --cached --quiet; then
  git commit -m " chore: deploy keyed LSH masking + no-plane persistence + tests"
else
  echo "[i] No changes to commit"
fi
git push "$GIT_REMOTE" "$GIT_BRANCH"

popd >/dev/null

echo "[+] Waiting ${WAIT_SECS}s for CI/CD to deploy..."
sleep "$WAIT_SECS"

# Discover Azure Container Instance FQDN if not provided
if [[ -z "$SERVER_URL" ]]; then
  if ! command -v az >/dev/null 2>&1; then
    echo "[-] Azure CLI not found. Install az or export SERVER_URL explicitly." >&2
    exit 2
  fi

  echo "[+] Querying Azure for container instances..."
  if [[ -n "$AZURE_RESOURCE_GROUP" ]]; then
    CJSON=$(az container list -g "$AZURE_RESOURCE_GROUP" -o json)
  else
    CJSON=$(az container list -o json)
  fi

  NAME=$(echo "$CJSON" | jq -r '[.[] | select(.name | test("secure-search"))][0].name')
  FQDN=$(echo "$CJSON" | jq -r '[.[] | select(.name | test("secure-search"))][0].ipAddress.fqdn')
  RG=$(echo "$CJSON" | jq -r '[.[] | select(.name | test("secure-search"))][0].resourceGroup')

  if [[ -z "$FQDN" || "$FQDN" == "null" ]]; then
    echo "[-] Could not find secure-search container FQDN. Export SERVER_URL and retry." >&2
    exit 3
  fi

  SERVER_URL="http://${FQDN}:8001"
  echo "[+] Discovered server: ${SERVER_URL} (name=${NAME}, rg=${RG})"
fi

# Health check
echo "[+] Health check: ${SERVER_URL}/health"
set +e
curl -sS "${SERVER_URL}/health" | sed -e 's/^/[health] /'
HC=$?
set -e
if [[ $HC -ne 0 ]]; then
  echo "[-] Health check failed with code $HC" >&2
fi

# Logs via Azure CLI if available
if command -v az >/dev/null 2>&1; then
  echo "[+] Fetching Azure container logs (best-effort)"
  if [[ -z "${RG:-}" || -z "${NAME:-}" ]]; then
    echo "[i] Skipping logs: missing resource group or container name"
  else
    az container logs -g "$RG" -n "$NAME" --tail 200 || true
  fi
fi

# Run pytest suite against Azure
pushd "$CLIENT_DIR" >/dev/null
export SECURE_SEARCH_SERVER_URL="$SERVER_URL"
if [[ -n "$DB_SERVER_API_KEY" ]]; then
  export DB_SERVER_API_KEY
fi
export SECURE_SEARCH_STRIP_PLAINTEXT_METADATA=1

./venv/bin/python3 -m pytest -q
PYRC=$?

popd >/dev/null

exit "$PYRC" 