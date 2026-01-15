#!/bin/bash
# Create Nextcloud database if it doesn't exist

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE nextcloud OWNER $POSTGRES_USER'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nextcloud')\gexec
EOSQL

echo "Nextcloud database ready"
