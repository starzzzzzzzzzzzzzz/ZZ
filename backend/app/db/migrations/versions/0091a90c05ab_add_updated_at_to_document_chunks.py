"""add updated_at to document_chunks

Revision ID: 0091a90c05ab
Revises: d01d06cbfcdb
Create Date: 2024-02-18 18:48:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = '0091a90c05ab'
down_revision: Union[str, None] = 'd01d06cbfcdb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 updated_at 列，默认值为当前时间
    op.add_column('document_chunks', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
    # 添加 onupdate 触发器，使得每次更新时自动更新 updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        CREATE TRIGGER update_document_chunks_updated_at
            BEFORE UPDATE ON document_chunks
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    # 删除触发器和函数
    op.execute("""
        DROP TRIGGER IF EXISTS update_document_chunks_updated_at ON document_chunks;
        DROP FUNCTION IF EXISTS update_updated_at_column();
    """)
    # 删除 updated_at 列
    op.drop_column('document_chunks', 'updated_at')
