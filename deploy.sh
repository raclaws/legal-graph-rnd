#!/bin/bash
# Deploy script — pulls latest images and starts containers.
# Secrets are fetched at boot by the backend via Infisical Python SDK.
# Only INFISICAL_CLIENT_ID and INFISICAL_CLIENT_SECRET are needed in .env on the host.

set -e

echo "Deploying..."

docker compose pull
docker compose up -d

echo "Done. Containers:"
docker compose ps
