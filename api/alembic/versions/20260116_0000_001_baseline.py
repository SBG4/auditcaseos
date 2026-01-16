"""Baseline migration - stamps existing schema

This migration represents the initial database state created by configs/postgres/init.sql.
It does not make any changes - it simply marks the current schema as the baseline
for future migrations to build upon.

Revision ID: 001
Revises: None
Create Date: 2026-01-16

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Baseline migration - no changes needed.

    The database schema was created by configs/postgres/init.sql which includes:
    - Extensions: uuid-ossp, pgvector
    - Enums: case_type, case_status, severity_level, evidence_type, etc.
    - Tables: users, scopes, cases, evidence, findings, audit_log, etc.
    - Indexes and foreign key constraints
    - Trigger functions for updated_at timestamps
    - Case ID generation function

    This migration simply stamps the current state as the baseline.
    Future migrations will build upon this.
    """
    pass


def downgrade() -> None:
    """
    Cannot downgrade from baseline.

    To fully reset the database, drop and recreate it,
    then re-run init.sql.
    """
    pass
