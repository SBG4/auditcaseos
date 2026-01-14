#!/bin/bash
# Create additional database for Paperless-ngx
# This script runs before init.sql (alphabetically)

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE paperless OWNER $POSTGRES_USER;
EOSQL

echo "Paperless database created successfully"
