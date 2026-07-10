#!/bin/bash
# Deploy script — pulls latest images and starts with secrets from Infisical
# Usage: ./deploy.sh [env]
# Requires: infisical CLI installed, authenticated (`infisical login`)

set -e

ENV="${1:-prod}"
PROJECT_ID="877bab29-028e-492d-aad1-acb44ca4f529"

echo "Deploying with env=$ENV..."

docker compose pull
infisical run --env="$ENV" --projectId="$PROJECT_ID" -- docker compose up -d

echo "Done. Containers:"
docker compose ps
