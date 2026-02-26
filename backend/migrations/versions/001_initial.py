"""Initial schema — users, reports, payments, batteries

Revision ID: 001_initial
Revises: 
Create Date: 2025-02-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ── Users ──────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # ── Reports ────────────────────────────────────────────────
    op.create_table(
        'reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('token', sa.String(64), nullable=False, unique=True),
        sa.Column('input_json', postgresql.JSON(), nullable=False),
        sa.Column('pdf_path', sa.String(512), nullable=True),
        sa.Column('status', sa.String(32), default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_reports_token', 'reports', ['token'])

    # ── Payments ───────────────────────────────────────────────
    op.create_table(
        'payments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('report_id', sa.String(36), sa.ForeignKey('reports.id'), nullable=False),
        sa.Column('paynow_payment_id', sa.String(128), nullable=True, unique=True),
        sa.Column('status', sa.String(32), default='NEW'),
        sa.Column('amount_groszy', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), default='PLN'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_payments_paynow_id', 'payments', ['paynow_payment_id'])

    # ── Batteries ──────────────────────────────────────────────
    op.create_table(
        'batteries',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('brand', sa.String(128), nullable=False),
        sa.Column('capacity_kwh', sa.Float(), nullable=False),
        sa.Column('price_pln', sa.Integer(), nullable=True),
        sa.Column('warranty_years', sa.Integer(), nullable=True),
        sa.Column('chemistry', sa.String(64), nullable=True),
        sa.Column('max_power_kw', sa.Float(), nullable=True),
        sa.Column('cycles', sa.Integer(), nullable=True),
        sa.Column('dod_percent', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.String(512), nullable=True),
        sa.Column('datasheet_url', sa.String(512), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('specs_json', postgresql.JSON(), nullable=True),
    )


def downgrade():
    op.drop_table('batteries')
    op.drop_table('payments')
    op.drop_table('reports')
    op.drop_table('users')
