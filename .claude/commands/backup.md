---
name: backup
description: Run full system backup
---

Backup AuditCaseOS data (PostgreSQL databases and MinIO buckets).

## Full Backup

```bash
./scripts/backup-all.sh
```

This runs both database and MinIO backups with 7-day retention.

## Individual Backups

```bash
# PostgreSQL only
./scripts/backup-database.sh

# MinIO only
./scripts/backup-minio.sh
```

## Restore

```bash
# Restore PostgreSQL (interactive - confirms before restore)
./scripts/restore-database.sh /path/to/backup.dump

# Restore MinIO bucket
./scripts/restore-minio.sh /path/to/minio-backup-dir
```

## Backup Location

```
backups/
├── postgres/
│   └── auditcaseos_YYYYMMDD_HHMMSS.dump
└── minio/
    └── evidence_YYYYMMDD_HHMMSS/
```

## Schedule Backups

Add to crontab for daily 2 AM backups:

```bash
0 2 * * * /path/to/auditcaseos/scripts/backup-all.sh >> /var/log/auditcaseos-backup.log 2>&1
```

## Test Backup Scripts

```bash
./scripts/test-backup.sh
```

Runs 42 test cases covering:
- Script syntax and permissions
- PostgreSQL backup/restore
- MinIO backup/restore
- Retention policy
