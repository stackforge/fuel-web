"""Upgrade
Revision ID: 596b7e3f2b11
Revises: 330ec2ab2bbf
Create Date: 2014-04-15 10:57:02.363048

"""

# revision identifiers, used by Alembic.
revision = '596b7e3f2b11'
down_revision = '330ec2ab2bbf'

from alembic import op
import sqlalchemy as sa

from nailgun.db.sqlalchemy.models.fields import JSON


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('releases',
                  sa.Column('api_version',
                            sa.String(length=30),
                            nullable=True))
    op.add_column('releases',
                  sa.Column('fuel_version',
                            JSON(),
                            nullable=True))
    op.add_column('releases',
                  sa.Column('pp_manifests_source',
                            sa.Unicode(length=255),
                            nullable=True))
    op.add_column('releases',
                  sa.Column('pp_modules_source',
                            sa.Unicode(length=255),
                            nullable=True))
    op.add_column('releases',
                  sa.Column('repo_metadata',
                            JSON(),
                            nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('releases', 'repo_metadata')
    op.drop_column('releases', 'pp_modules_source')
    op.drop_column('releases', 'pp_manifests_source')
    op.drop_column('releases', 'api_version')
    op.drop_column('releases', 'fuel_version')
    ### end Alembic commands ###
