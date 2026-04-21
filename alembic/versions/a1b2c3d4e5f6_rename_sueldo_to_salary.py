"""rename sueldo to salary

Revision ID: a1b2c3d4e5f6
Revises: 37f969dd0def
Create Date: 2026-04-18 00:00:00.000000

"""
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = '37f969dd0def'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('users', 'sueldo', new_column_name='salary')


def downgrade() -> None:
    op.alter_column('users', 'salary', new_column_name='sueldo')
