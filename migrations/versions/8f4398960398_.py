"""empty message

Revision ID: 8f4398960398
Revises: af94f198c2c3
Create Date: 2020-05-04 12:37:06.309307

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8f4398960398'
down_revision = 'af94f198c2c3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('api_token', sa.String(length=36), nullable=True))
    op.add_column('user', sa.Column('email_token', sa.String(length=36), nullable=True))
    op.drop_index('token', table_name='user')
    op.create_unique_constraint(None, 'user', ['api_token'])
    op.create_unique_constraint(None, 'user', ['email_token'])
    op.drop_column('user', 'token')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('token', mysql.VARCHAR(length=36), nullable=True))
    op.drop_constraint(None, 'user', type_='unique')
    op.drop_constraint(None, 'user', type_='unique')
    op.create_index('token', 'user', ['token'], unique=True)
    op.drop_column('user', 'email_token')
    op.drop_column('user', 'api_token')
    # ### end Alembic commands ###