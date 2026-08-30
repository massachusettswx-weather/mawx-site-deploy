#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/model-cloudrun"

PROJECT_ID="$(gcloud config get-value project)"
REGION="us-east1"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/weather-jobs/model-pipelines:latest"

echo
echo "===== COMPILE ====="

python3 -m py_compile \
  cloud_job.py \
  shared/operational.py \
  shared/product_cadence.py \
  shared/resume.py \
  shared/runner.py \
  ifs/run.py \
  aifs/run.py

echo "Compile passed."

echo
echo "===== BUILD IMAGE ====="

gcloud builds submit \
  --tag="$IMAGE"

echo
echo "===== UPDATE CLOUD RUN JOBS ====="

for JOB in masswx-ifs masswx-aifs; do

  echo
  echo "Updating $JOB..."

  gcloud run jobs update "$JOB" \
    --region="$REGION" \
    --image="$IMAGE" \
    --task-timeout=6h \
    --max-retries=2 \
    --cpu=2 \
    --memory=4Gi

done

echo
echo "===== ENABLE SCHEDULERS ====="

for SCHED in masswx-ifs-refresh masswx-aifs-refresh; do

  gcloud scheduler jobs resume "$SCHED" \
    --location="$REGION"

done

echo
echo "===== FINAL STATUS ====="

for JOB in masswx-ifs masswx-aifs; do

  echo
  echo "----- $JOB -----"

  gcloud run jobs describe "$JOB" \
    --region="$REGION" \
    | grep -E \
    'Image:|Memory:|CPU:|Task Timeout:|Max Retries:'

done

echo

for SCHED in masswx-ifs-refresh masswx-aifs-refresh; do

  echo "----- $SCHED -----"

  gcloud scheduler jobs describe "$SCHED" \
    --location="$REGION" \
    --format='value(state,schedule,timeZone)'

done

echo
echo "IFS/AIFS deployment complete."
