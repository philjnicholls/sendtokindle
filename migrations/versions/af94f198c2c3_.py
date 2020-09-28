"""empty message

Revision ID: af94f198c2c3
Revises: c3574f8c022b
Create Date: 2020-05-04 12:30:59.068021

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af94f198c2c3'
down_revision = 'c3574f8c022b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('kindle_email', sa.String(length=120), nullable=True))
    op.create_index(op.f('ix_user_kindle_email'), 'user', ['kindle_email'], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_user_kindle_email'), table_name='user')
    op.drop_column('user', 'kindle_email')
    # ### end Alembic commands ###