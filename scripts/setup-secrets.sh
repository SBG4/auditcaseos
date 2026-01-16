#!/bin/bash
# AuditCaseOS - Secret Management Setup
# This script sets up the secrets infrastructure for the first time

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SECRETS_DIR="$PROJECT_ROOT/secrets"
AGE_KEY_DIR="$HOME/.config/sops/age"
AGE_KEY_FILE="$AGE_KEY_DIR/keys.txt"

echo "=== AuditCaseOS Secret Management Setup ==="
echo ""

# Check for required tools
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: $1 is not installed."
        echo "Install with: brew install $1 (macOS) or download from GitHub"
        exit 1
    fi
}

echo "1. Checking required tools..."
check_tool "sops"
check_tool "age"
echo "   - sops: OK"
echo "   - age: OK"
echo ""

# Generate age key if not exists
echo "2. Checking age keypair..."
if [ -f "$AGE_KEY_FILE" ]; then
    echo "   - Age key already exists at $AGE_KEY_FILE"
else
    echo "   - Generating new age keypair..."
    mkdir -p "$AGE_KEY_DIR"
    age-keygen -o "$AGE_KEY_FILE"
    chmod 600 "$AGE_KEY_FILE"
    echo "   - Key generated at $AGE_KEY_FILE"
fi

# Extract public key
PUBLIC_KEY=$(grep "public key:" "$AGE_KEY_FILE" | cut -d: -f2 | tr -d ' ')
echo "   - Your public key: $PUBLIC_KEY"
echo ""

# Update .sops.yaml with the public key
echo "3. Updating .sops.yaml with your public key..."
if grep -q "age1placeholder" "$PROJECT_ROOT/.sops.yaml"; then
    sed -i.bak "s/age1placeholder_replace_with_your_public_key/$PUBLIC_KEY/" "$PROJECT_ROOT/.sops.yaml"
    rm -f "$PROJECT_ROOT/.sops.yaml.bak"
    echo "   - Updated .sops.yaml"
else
    echo "   - .sops.yaml already configured (no placeholder found)"
fi
echo ""

# Create encrypted secrets from template
echo "4. Creating encrypted secrets file..."
if [ -f "$SECRETS_DIR/development.enc.yaml" ]; then
    echo "   - development.enc.yaml already exists, skipping"
else
    if [ -f "$SECRETS_DIR/development.template.yaml" ]; then
        cp "$SECRETS_DIR/development.template.yaml" "$SECRETS_DIR/development.enc.yaml"
        sops -e -i "$SECRETS_DIR/development.enc.yaml"
        echo "   - Created and encrypted development.enc.yaml"
    else
        echo "   - ERROR: Template file not found"
        exit 1
    fi
fi
echo ""

# Decrypt secrets for immediate use
echo "5. Decrypting secrets for Docker Compose..."
"$SCRIPT_DIR/decrypt-secrets.sh"
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Review secrets in secrets/development.enc.yaml (edit with: sops secrets/development.enc.yaml)"
echo "2. Start the application: docker compose up -d"
echo "3. For production, create secrets/production.enc.yaml with different keys"
echo ""
echo "Your public key (share with team): $PUBLIC_KEY"
