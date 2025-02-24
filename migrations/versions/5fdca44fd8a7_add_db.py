"""add db

Revision ID: 5fdca44fd8a7
Revises: 22c0dd5e5324
Create Date: 2025-01-28 00:05:21.261752

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5fdca44fd8a7'
down_revision = '22c0dd5e5324'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ingredient',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('quantity', sa.String(length=50), nullable=False),
    sa.Column('menu_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['menu_id'], ['menu.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('menu', schema=None) as batch_op:
        batch_op.drop_column('ingre')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('menu', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ingre', sa.VARCHAR(), autoincrement=False, nullable=False))

    op.drop_table('ingredient')
    # ### end Alembic commands ###
