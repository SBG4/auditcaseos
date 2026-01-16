#!/bin/bash
# AuditCaseOS - Decrypt Secrets for Docker Compose
# This script decrypts the encrypted secrets file to individual .txt files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SECRETS_DIR="$PROJECT_ROOT/secrets"
SECRETS_FILE="$SECRETS_DIR/development.enc.yaml"

# Check if encrypted secrets file exists
if [ ! -f "$SECRETS_FILE" ]; then
    echo "ERROR: Encrypted secrets file not found at $SECRETS_FILE"
    echo "Run ./scripts/setup-secrets.sh first to create it."
    exit 1
fi

# Check for sops
if ! command -v sops &> /dev/null; then
    echo "ERROR: sops is not installed."
    echo "Install with: brew install sops"
    exit 1
fi

echo "Decrypting secrets from $SECRETS_FILE..."

# Decrypt the YAML file
DECRYPTED=$(sops -d "$SECRETS_FILE")

# Extract each secret to its own file
extract_secret() {
    local key=$1
    local file=$2
    echo "$DECRYPTED" | grep "^$key:" | cut -d'"' -f2 > "$SECRETS_DIR/$file"
    chmod 600 "$SECRETS_DIR/$file"
    echo "  - $file"
}

extract_secret "postgres_password" "postgres_password.txt"
extract_secret "jwt_secret" "jwt_secret.txt"
extract_secret "minio_password" "minio_password.txt"
extract_secret "paperless_secret" "paperless_secret.txt"
extract_secret "paperless_admin_pass" "paperless_admin_pass.txt"
extract_secret "nextcloud_admin_pass" "nextcloud_admin_pass.txt"
extract_secret "onlyoffice_jwt" "onlyoffice_jwt.txt"

echo ""
echo "Secrets decrypted to $SECRETS_DIR/*.txt"
echo "These files are gitignored and will be mounted by Docker Compose."
