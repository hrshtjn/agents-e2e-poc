#!/usr/bin/env bash
# =============================================================================
# deploy_cloud_run.sh — Build and deploy the procurement agent to Cloud Run
#
# Usage:
#   ./deployment/deploy_cloud_run.sh [--project PROJECT_ID] [--region REGION]
#
# Defaults:
#   PROJECT_ID  → current gcloud project
#   REGION      → us-east1
# =============================================================================
set -euo pipefail

# ── Config (override via flags or env vars) ───────────────────────────────────
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${CLOUD_RUN_REGION:-us-east1}"
SERVICE_NAME="procurement-agent"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Parse optional flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT_ID="$2"; shift 2 ;;
    --region)  REGION="$2";     shift 2 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Deploying: ${SERVICE_NAME}"
echo "  Project:   ${PROJECT_ID}"
echo "  Region:    ${REGION}"
echo "  Image:     ${IMAGE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Enable required APIs ───────────────────────────────────────────────────
echo ""
echo "▶ Step 1/4 — Enabling Cloud Run & Artifact Registry APIs..."
gcloud services enable run.googleapis.com containerregistry.googleapis.com \
  --project="${PROJECT_ID}" --quiet

# ── 2. Build & push the image ─────────────────────────────────────────────────
echo ""
echo "▶ Step 2/4 — Building Docker image..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

gcloud builds submit "${REPO_ROOT}" \
  --tag="${IMAGE}" \
  --project="${PROJECT_ID}"

# ── 3. Deploy to Cloud Run ────────────────────────────────────────────────────
echo ""
echo "▶ Step 3/4 — Deploying to Cloud Run..."

# Read env vars from app/.env, skip comments and blank lines
ENV_VARS=""
ENV_FILE="${REPO_ROOT}/app/.env"
if [[ -f "${ENV_FILE}" ]]; then
  while IFS= read -r line; do
    # Skip comments and empty lines
    [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
    # Extract key=value pairs
    key="${line%%=*}"
    value="${line#*=}"
    # Skip if value is empty (not yet configured)
    [[ -z "$value" ]] && continue
    ENV_VARS="${ENV_VARS}${key}=${value},"
  done < "${ENV_FILE}"
  # Strip trailing comma
  ENV_VARS="${ENV_VARS%,}"
fi

DEPLOY_ARGS=(
  "${SERVICE_NAME}"
  "--image=${IMAGE}"
  "--region=${REGION}"
  "--project=${PROJECT_ID}"
  "--platform=managed"
  "--memory=1Gi"
  "--cpu=1"
  "--min-instances=0"
  "--max-instances=3"
  "--port=8080"
  "--timeout=300"
  # Use Workload Identity for GCP auth — no service account key needed
  "--service-account=${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com"
  "--no-allow-unauthenticated"  # Require IAM auth (change to --allow-unauthenticated for open access)
)

# Append env vars if any were read from .env
if [[ -n "${ENV_VARS}" ]]; then
  DEPLOY_ARGS+=("--set-env-vars=${ENV_VARS}")
fi

gcloud run deploy "${DEPLOY_ARGS[@]}"

# ── 4. Print service URL ──────────────────────────────────────────────────────
echo ""
echo "▶ Step 4/4 — Fetching service URL..."
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Deployment complete!"
echo "  🌐 Service URL: ${SERVICE_URL}"
echo ""
echo "  To test (requires IAM auth):"
echo "    curl -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" \\"
echo "      ${SERVICE_URL}"
echo ""
echo "  To open in browser (generates a short-lived token):"
echo "    gcloud run services proxy ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
