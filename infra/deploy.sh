#!/usr/bin/env bash
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-last-seen-alive}"

gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project "${GOOGLE_CLOUD_PROJECT}" \
  --region "${GOOGLE_CLOUD_LOCATION}" \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 4 \
  --cpu 1 \
  --memory 1Gi \
  --timeout 900 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION}" \
  --set-secrets "PARALLEL_API_KEY=parallel-api-key:latest,API_KEY_PEPPER=last-seen-alive-key-pepper:latest"

