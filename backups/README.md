# AuditCaseOS Backups

This directory contains automated backups of PostgreSQL databases and MinIO object storage.

## Directory Structure

```
backups/
├── postgres/           # PostgreSQL database backups
│   └── auditcaseos_YYYYMMDD_HHMMSS.dump
│   └── paperless_YYYYMMDD_HHMMSS.dump
│   └── nextcloud_YYYYMMDD_HHMMSS.dump
└── minio/              # MinIO bucket backups
    └── evidence_YYYYMMDD_HHMMSS/
        └── [mirrored files]
```

## Backup Scripts

| Script | Description |
|--------|-------------|
| `scripts/backup-database.sh` | Backup PostgreSQL databases |
| `scripts/backup-minio.sh` | Backup MinIO buckets |
| `scripts/backup-all.sh` | Run all backups |
| `scripts/restore-database.sh` | Restore PostgreSQL from backup |
| `scripts/restore-minio.sh` | Restore MinIO from backup |

## Quick Start

### Run Full Backup
```bash
./scripts/backup-all.sh
```

### Run Individual Backups
```bash
./scripts/backup-database.sh  # PostgreSQL only
./scripts/backup-minio.sh     # MinIO only
```

### Restore Database
```bash
./scripts/restore-database.sh ./backups/postgres/auditcaseos_20260116_120000.dump
```

### Restore MinIO Bucket
```bash
./scripts/restore-minio.sh ./backups/minio/evidence_20260116_120000
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKUP_DIR` | `./backups` | Base backup directory |
| `RETENTION_DAYS` | `7` | Days to keep backups |
| `CONTAINER_NAME` | varies | Docker container name |
| `POSTGRES_USER` | `auditcaseos` | PostgreSQL user |

## Scheduling

Add to crontab for daily backups at 2 AM:

```bash
crontab -e
# Add:
0 2 * * * /path/to/auditcaseos/scripts/backup-all.sh >> /var/log/auditcaseos-backup.log 2>&1
```

## Retention Policy

- Backups older than 7 days are automatically deleted
- Adjust with `RETENTION_DAYS` environment variable

## Notes

- PostgreSQL backups use `pg_dump` with custom format (-Fc) for compression
- MinIO backups use `mc mirror` (NOT Docker volume backup) to preserve metadata
- Always verify backups periodically by testing restore procedures
