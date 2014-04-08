"""patch_openstack

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


old_cluster_status_options = (
    'new',
    'deployment',
    'operational',
    'error',
    'remove',
    'stopped'
)
new_cluster_status_options = sorted(
    old_cluster_status_options + ('update',)
)

old_task_names_options = (
    'super',
    'deploy',
    'deployment',
    'provision',
    'node_deletion',
    'cluster_deletion',
    'check_before_deployment',
    'check_networks',
    'verify_networks',
    'check_dhcp',
    'verify_network_connectivity',
    'redhat_setup',
    'redhat_check_credentials',
    'redhat_check_licenses',
    'redhat_download_release',
    'redhat_update_cobbler_profile',
    'dump',
    'capacity_log',
    'stop_deployment',
    'reset_environment'
)
new_task_names_options = sorted(
    old_task_names_options + ('update',)
)


def upgrade_enum(table, column_name, enum_name, old_options, new_options):
    old_type = sa.Enum(*old_options, name=enum_name)
    new_type = sa.Enum(*new_options, name=enum_name)
    tmp_type = sa.Enum(*new_options, name="_" + enum_name)
    # Create a tempoary type, convert and drop the "old" type
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        u'ALTER TABLE {0} ALTER COLUMN {1} TYPE _{2}'
        u' USING {1}::text::_{2}'.format(
            table,
            column_name,
            enum_name
        )
    )
    old_type.drop(op.get_bind(), checkfirst=False)
    # Create and convert to the "new" type
    new_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        u'ALTER TABLE {0} ALTER COLUMN {1} TYPE {2}'
        u' USING {1}::text::{2}'.format(
            table,
            column_name,
            enum_name
        )
    )
    tmp_type.drop(op.get_bind(), checkfirst=False)


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clusters',
                  sa.Column('pending_release_id',
                            sa.Integer(),
                            nullable=True))

    op.add_column('releases',
                  sa.Column('can_update_openstack_versions',
                            JSON(),
                            nullable=True))
    op.add_column('releases',
                  sa.Column('api_version',
                            sa.String(length=30),
                            nullable=True))
    op.add_column('releases',
                  sa.Column('fuel_version',
                            JSON(),
                            nullable=True))
    op.add_column('releases',
                  sa.Column('openstack_version',
                            sa.String(length=30),
                            nullable=False))
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
    op.drop_column('releases', 'version')
    op.create_unique_constraint(None,
                                'releases',
                                ['name', 'openstack_version'])

    # CLUSTER STATUS ENUM UPGRADE
    upgrade_enum(
        "clusters",                  # table
        "status",                    # column
        "cluster_status",            # ENUM name
        old_cluster_status_options,  # old options
        new_cluster_status_options   # new options
    )
    # TASK NAME ENUM UPGRADE
    upgrade_enum(
        "tasks",                     # table
        "name",                      # column
        "task_name",                 # ENUM name
        old_task_names_options,      # old options
        new_task_names_options       # new options
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('releases',
                  sa.Column('version',
                            sa.VARCHAR(length=30),
                            nullable=False))
    op.drop_column('releases', 'repo_metadata')
    op.drop_column('releases', 'pp_modules_source')
    op.drop_column('releases', 'pp_manifests_source')
    op.drop_column('releases', 'openstack_version')
    op.drop_column('releases', 'can_update_openstack_versions')
    op.drop_column('releases', 'api_version')
    op.drop_column('releases', 'fuel_version')

    # CLUSTER STATUS ENUM DOWNGRADE
    upgrade_enum(
        "clusters",                  # table
        "status",                    # column
        "cluster_status",            # ENUM name
        new_cluster_status_options,  # old options
        old_cluster_status_options   # new options
    )
    # TASK NAME ENUM DOWNGRADE
    upgrade_enum(
        "tasks",                     # table
        "name",                      # column
        "task_name",                 # ENUM name
        new_task_names_options,      # old options
        old_task_names_options       # new options
    )
    ### end Alembic commands ###
