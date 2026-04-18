"""initial_schema

Revision ID: 21b26210721d
Revises:
Create Date: 2026-04-18 12:45:26.943710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21b26210721d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users first (no FK to couples yet — added below to break the cycle)
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('firebase_uid', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('couple_id', sa.UUID(), nullable=True),
    sa.Column('sueldo', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('firebase_uid')
    )
    op.create_table('couples',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user1_id', sa.UUID(), nullable=False),
    sa.Column('user2_id', sa.UUID(), nullable=True),
    sa.Column('split_mode', sa.Enum('auto', 'equal', 'custom', name='splitmode', native_enum=False), nullable=False),
    sa.Column('percentage_user1', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('percentage_user2', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('invite_code', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['user1_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['user2_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('invite_code')
    )
    # Add the deferred FK from users.couple_id → couples.id
    op.create_foreign_key('fk_users_couple_id', 'users', 'couples', ['couple_id'], ['id'])
    op.create_table('expenses',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('couple_id', sa.UUID(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('type', sa.Enum('shared', 'personal', name='expensetype', native_enum=False), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('paid_by', sa.UUID(), nullable=False),
    sa.Column('split_override_user1', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('split_override_user2', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.ForeignKeyConstraint(['couple_id'], ['couples.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['paid_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('expenses')
    op.drop_constraint('fk_users_couple_id', 'users', type_='foreignkey')
    op.drop_table('couples')
    op.drop_table('users')
