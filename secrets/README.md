# AuditCaseOS Secrets Management

This directory contains encrypted secrets using SOPS + age.

## Prerequisites

Install SOPS and age:

```bash
# macOS
brew install sops age

# Linux
# Download from https://github.com/getsops/sops/releases
# Download from https://github.com/FiloSottile/age/releases
```

## Initial Setup (First Time)

1. Generate an age keypair:
```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
```

2. Get your public key:
```bash
grep "public key:" ~/.config/sops/age/keys.txt
# Output: age1abc123...
```

3. Add your public key to `.sops.yaml` in the project root.

4. Create encrypted secrets:
```bash
cd secrets
sops development.enc.yaml
```

## Decrypting Secrets for Development

```bash
# Decrypt all secrets to .txt files
./scripts/decrypt-secrets.sh

# Or decrypt manually
sops -d secrets/development.enc.yaml > secrets/development.yaml
```

## Starting Docker Compose with Secrets

```bash
# Option 1: Decrypt first, then start
./scripts/decrypt-secrets.sh
docker compose up -d

# Option 2: Use sops exec-env (injects as env vars)
sops exec-env secrets/development.enc.yaml 'docker compose up -d'
```

## Secret Files

| File | Purpose |
|------|---------|
| `development.enc.yaml` | Encrypted development secrets |
| `production.enc.yaml` | Encrypted production secrets (template) |
| `*.txt` | Decrypted individual secrets (gitignored) |

## Secrets Included

- `postgres_password` - PostgreSQL database password
- `jwt_secret` - API JWT signing key
- `minio_password` - MinIO root password
- `paperless_secret` - Paperless-ngx secret key
- `paperless_admin_pass` - Paperless admin password
- `nextcloud_admin_pass` - Nextcloud admin password
- `onlyoffice_jwt` - ONLYOFFICE JWT secret

## Rotating Secrets

1. Edit the encrypted file:
```bash
sops secrets/development.enc.yaml
```

2. Decrypt and restart containers:
```bash
./scripts/decrypt-secrets.sh
docker compose down && docker compose up -d
```

## Security Notes

- **NEVER** commit decrypted `.txt` or `.yaml` files
- **NEVER** commit your age private key (`keys.txt`)
- Keep production keys separate from development keys
- Use different age keys for CI/CD vs local development
