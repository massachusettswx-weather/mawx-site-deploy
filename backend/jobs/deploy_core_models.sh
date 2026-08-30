#!/usr/bin/env bash
set -euo pipefail

REGION="us-east1"
PROJECT_ID="$(gcloud config get-value project)"
REPOSITORY="weather-jobs"
IMAGE_NAME="model-pipelines"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest"

echo "============================================================"
echo " MASSACHUSETTSWX CORE MODEL DEPLOYMENT"
echo "============================================================"
echo
echo "Project: ${PROJECT_ID}"
echo "Image:   ${IMAGE}"
echo

echo "Building shared model image..."
gcloud builds submit \
    --tag="${IMAGE}" \
    .

echo
echo "Updating Cloud Run jobs..."

for JOB in \
    masswx-gfs \
    masswx-ifs \
    masswx-aifs
do
    echo
    echo "Updating ${JOB}..."

    gcloud run jobs update "${JOB}" \
        --region="${REGION}" \
        --image="${IMAGE}"
done

echo
echo "============================================================"
echo " DEPLOYMENT COMPLETE"
echo "============================================================"
echo
echo "GFS  -> masswx-gfs"
echo "IFS  -> masswx-ifs"
echo "AIFS -> masswx-aifs"
echo
echo "Schedulers remain responsible for execution."
