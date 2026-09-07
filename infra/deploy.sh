#!/usr/bin/env bash
# Deploy Last Seen Alive to Cloud Run.
#
# `gcloud run deploy --set-env-vars` and `--set-secrets` REPLACE the existing
# sets rather than merging into them, so every variable the service needs has to
# be listed here. An earlier version of this script omitted three of them and
# named the Parallel secret incorrectly, which meant running it would have taken
# a working service down.
#
# Sizing note. /v1/investigate accepts a 48 MB fragment and holds it in memory for
# the length of the request, and on Cloud Run the filesystem is memory-backed too.
# At the platform default of 80 concurrent requests per instance that is nearly
# 4 GB of fragment data against a 1 GB limit -- an out-of-memory button rather
# than a rate limit. Concurrency is capped at 8 and memory raised to 2 GB.
# Investigations are I/O-bound on Gemini and Parallel, so 8 per instance across
# 4 instances is far more headroom than a demo needs.
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-last-seen-alive}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-lsa-runtime@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash}"

PARALLEL_SECRET="${PARALLEL_SECRET:-last-seen-alive-parallel-api-key}"
PEPPER_SECRET="${PEPPER_SECRET:-last-seen-alive-key-pepper}"

secrets="API_KEY_PEPPER=${PEPPER_SECRET}:latest"

# The Parallel credential is mandatory for the workflow but is an owner-supplied
# secret. Deploying without it produces a service that reports the integration
# unavailable and refuses to investigate, which is the correct degraded state —
# far better than a deploy that fails outright and leaves the old revision up
# with no explanation.
if gcloud secrets describe "${PARALLEL_SECRET}" --project "${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1; then
  secrets="PARALLEL_API_KEY=${PARALLEL_SECRET}:latest,${secrets}"
  echo "Parallel credential found: binding ${PARALLEL_SECRET} to PARALLEL_API_KEY."
else
  echo "WARNING: secret ${PARALLEL_SECRET} does not exist in ${GOOGLE_CLOUD_PROJECT}."
  echo "         Deploying without it. /health/integrations will report Parallel"
  echo "         unavailable and POST /v1/identify will return 503. Create the"
  echo "         secret and re-run this script to activate the partner runtime."
fi

gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project "${GOOGLE_CLOUD_PROJECT}" \
  --region "${GOOGLE_CLOUD_LOCATION}" \
  --service-account "${SERVICE_ACCOUNT}" \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 4 \
  --cpu 1 \
  --memory 2Gi \
  --concurrency 8 \
  --timeout 900 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION},GOOGLE_GENAI_USE_VERTEXAI=true,GEMINI_MODEL=${GEMINI_MODEL}" \
  --set-secrets "${secrets}"

echo
echo "Verifying the deployed runtime:"
url="$(gcloud run services describe "${SERVICE_NAME}" \
  --project "${GOOGLE_CLOUD_PROJECT}" --region "${GOOGLE_CLOUD_LOCATION}" \
  --format 'value(status.url)')"
curl -fsS "${url}/health/integrations" | tee /dev/stderr >/dev/null
echo
echo "Product:   ${url}"
echo "API docs:  ${url}/docs"
echo "Stack:     ${url}/stack"
