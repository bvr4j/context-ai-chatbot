"""Initial schema for conversations and messages

Revision ID: 001_initial
Revises: 
Create Date: 2026-10-31 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "conversations" not in existing_tables:
        op.create_table(
            'conversations',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('title', sa.String(length=255), server_default='New Conversation', nullable=False),
            sa.Column('mode', sa.String(length=20), server_default='balanced', nullable=False),
            sa.Column('summary', sa.Text(), server_default='', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

    if "messages" not in existing_tables:
        op.create_table(
            'messages',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('conversation_id', sa.String(length=36), nullable=False),
            sa.Column('role', sa.String(length=20), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('mode', sa.String(length=20), nullable=True),
            sa.Column('model_label', sa.String(length=100), nullable=True),
            sa.Column('is_archived', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
        op.create_index(op.f('ix_messages_is_archived'), 'messages', ['is_archived'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_messages_is_archived'), table_name='messages')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_table('conversations')
