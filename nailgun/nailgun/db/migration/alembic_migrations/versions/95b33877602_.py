"""empty message

Revision ID: 95b33877602
Revises: 58c8dbea159d
Create Date: 2014-02-03 19:44:27.443033

"""

# revision identifiers, used by Alembic.
revision = '95b33877602'
down_revision = '58c8dbea159d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('clusters_name_key', 'clusters')
    op.create_unique_constraint(None, 'clusters', ['name'])
    op.add_column('nodes', sa.Column('cached', sa.String(length=40), nullable=True))
    op.drop_index('nodes_mac_key', 'nodes')
    op.create_unique_constraint(None, 'nodes', ['mac'])
    op.drop_index('plugins_name_key', 'plugins')
    op.create_unique_constraint(None, 'plugins', ['name'])
    op.drop_index('releases_name_version_key', 'releases')
    op.create_unique_constraint(None, 'releases', ['name', 'version'])
    op.drop_index('roles_name_release_id_key', 'roles')
    op.create_unique_constraint(None, 'roles', ['name', 'release_id'])
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'roles')
    op.create_index('roles_name_release_id_key', 'roles', [u'release_id', u'name'], unique=True)
    op.drop_constraint(None, 'releases')
    op.create_index('releases_name_version_key', 'releases', [u'name', u'version'], unique=True)
    op.drop_constraint(None, 'plugins')
    op.create_index('plugins_name_key', 'plugins', [u'name'], unique=True)
    op.drop_constraint(None, 'nodes')
    op.create_index('nodes_mac_key', 'nodes', [u'mac'], unique=True)
    op.drop_column('nodes', 'cached')
    op.drop_constraint(None, 'clusters')
    op.create_index('clusters_name_key', 'clusters', [u'name'], unique=True)
    ### end Alembic commands ###
