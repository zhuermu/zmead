"""Initial database schema with all models.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-11-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('avatar_url', sa.String(512), nullable=True),
        sa.Column('oauth_provider', sa.String(50), nullable=False, server_default='google'),
        sa.Column('oauth_id', sa.String(255), nullable=False),
        sa.Column('gifted_credits', sa.Numeric(10, 2), nullable=False, server_default='500.00'),
        sa.Column('purchased_credits', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('notification_preferences', mysql.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_oauth_id', 'users', ['oauth_id'], unique=False)

    # Create ad_accounts table
    op.create_table(
        'ad_accounts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('platform_account_id', sa.String(255), nullable=False),
        sa.Column('account_name', sa.String(255), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_ad_accounts_user_id', 'ad_accounts', ['user_id'], unique=False)

    # Create landing_pages table
    op.create_table(
        'landing_pages',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(1024), nullable=False),
        sa.Column('s3_key', sa.String(512), nullable=False),
        sa.Column('product_url', sa.String(1024), nullable=False),
        sa.Column('template', sa.String(100), nullable=False, server_default='modern'),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('html_content', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_landing_pages_user_id', 'landing_pages', ['user_id'], unique=False)

    # Create creatives table
    op.create_table(
        'creatives',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('file_url', sa.String(1024), nullable=False),
        sa.Column('cdn_url', sa.String(1024), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('product_url', sa.String(1024), nullable=True),
        sa.Column('style', sa.String(100), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('tags', mysql.JSON(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_creatives_user_id', 'creatives', ['user_id'], unique=False)

    # Create campaigns table
    op.create_table(
        'campaigns',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('ad_account_id', sa.BigInteger(), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('platform_campaign_id', sa.String(255), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('objective', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('budget', sa.Numeric(10, 2), nullable=False),
        sa.Column('budget_type', sa.String(50), nullable=False, server_default='daily'),
        sa.Column('targeting', mysql.JSON(), nullable=False),
        sa.Column('creative_ids', mysql.JSON(), nullable=False),
        sa.Column('landing_page_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ad_account_id'], ['ad_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['landing_page_id'], ['landing_pages.id'], ondelete='SET NULL')
    )
    op.create_index('ix_campaigns_user_id', 'campaigns', ['user_id'], unique=False)
    op.create_index('ix_campaigns_ad_account_id', 'campaigns', ['ad_account_id'], unique=False)

    # Create report_metrics table
    op.create_table(
        'report_metrics',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('ad_account_id', sa.BigInteger(), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('entity_name', sa.String(255), nullable=False),
        sa.Column('impressions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('clicks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('spend', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('conversions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('revenue', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('ctr', sa.Float(), nullable=False, server_default='0'),
        sa.Column('cpc', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('cpa', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('roas', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_metrics_timestamp', 'report_metrics', ['timestamp'], unique=False)
    op.create_index('ix_report_metrics_user_id', 'report_metrics', ['user_id'], unique=False)
    op.create_index('ix_report_metrics_ad_account_id', 'report_metrics', ['ad_account_id'], unique=False)
    op.create_index('ix_report_metrics_entity_id', 'report_metrics', ['entity_id'], unique=False)
    op.create_index('ix_report_metrics_user_timestamp', 'report_metrics', ['user_id', 'timestamp'], unique=False)
    op.create_index('ix_report_metrics_account_timestamp', 'report_metrics', ['ad_account_id', 'timestamp'], unique=False)
    op.create_index('ix_report_metrics_entity', 'report_metrics', ['entity_type', 'entity_id', 'timestamp'], unique=False)

    # Create credit_transactions table
    op.create_table(
        'credit_transactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('from_gifted', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('from_purchased', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('balance_after', sa.Numeric(10, 2), nullable=False),
        sa.Column('operation_type', sa.String(100), nullable=True),
        sa.Column('operation_id', sa.String(255), nullable=True),
        sa.Column('details', mysql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_credit_transactions_user_id', 'credit_transactions', ['user_id'], unique=False)
    op.create_index('ix_credit_transactions_user_created', 'credit_transactions', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_credit_transactions_type', 'credit_transactions', ['type'], unique=False)

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('action_url', sa.String(1024), nullable=True),
        sa.Column('action_text', sa.String(100), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('sent_via', mysql.JSON(), nullable=False),
        sa.Column('extra_data', mysql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)
    op.create_index('ix_notifications_user_read', 'notifications', ['user_id', 'is_read'], unique=False)
    op.create_index('ix_notifications_user_created', 'notifications', ['user_id', 'created_at'], unique=False)

    # Create credit_config table
    op.create_table(
        'credit_config',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('gemini_flash_input_rate', sa.Numeric(10, 4), nullable=False, server_default='0.01'),
        sa.Column('gemini_flash_output_rate', sa.Numeric(10, 4), nullable=False, server_default='0.04'),
        sa.Column('gemini_pro_input_rate', sa.Numeric(10, 4), nullable=False, server_default='0.05'),
        sa.Column('gemini_pro_output_rate', sa.Numeric(10, 4), nullable=False, server_default='0.2'),
        sa.Column('image_generation_rate', sa.Numeric(10, 2), nullable=False, server_default='0.5'),
        sa.Column('video_generation_rate', sa.Numeric(10, 2), nullable=False, server_default='5'),
        sa.Column('landing_page_rate', sa.Numeric(10, 2), nullable=False, server_default='15'),
        sa.Column('competitor_analysis_rate', sa.Numeric(10, 2), nullable=False, server_default='10'),
        sa.Column('optimization_suggestion_rate', sa.Numeric(10, 2), nullable=False, server_default='20'),
        sa.Column('registration_bonus', sa.Numeric(10, 2), nullable=False, server_default='500'),
        sa.Column('packages', mysql.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('credit_config')
    op.drop_table('notifications')
    op.drop_table('credit_transactions')
    op.drop_table('report_metrics')
    op.drop_table('campaigns')
    op.drop_table('creatives')
    op.drop_table('landing_pages')
    op.drop_table('ad_accounts')
    op.drop_table('users')
