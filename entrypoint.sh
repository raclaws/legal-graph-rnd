#!/bin/sh
# Copy seed DB to volume if not present
if [ ! -f /app/data/legal.db ]; then
    mkdir -p /app/data
    cp /app/_seed_legal.db /app/data/legal.db
fi

exec "$@"
