#!/bin/sh

echo "*:*:*:${NAILGUN_DB_ROOT}:${NAILGUN_DB_ROOTPW}" > ${NAILGUN_DB_ROOTPGPASS}
chmod 600 ${NAILGUN_DB_ROOTPGPASS}

echo "Trying to find out if role ${NAILGUN_DB_USER} exists"
PGPASSFILE=${NAILGUN_DB_ROOTPGPASS} root_roles=$(psql -U postgres -t -c "SELECT 'HERE' from pg_roles where rolname='${NAILGUN_DB_USER}'")
if [[ ${root_roles} == *HERE ]];then
  echo "Role ${NAILGUN_DB_USER} exists. Setting password ${NAILGUN_DB_PW}"
  PGPASSFILE=${NAILGUN_DB_ROOTPGPASS} psql -h 127.0.0.1 -U postgres -c "ALTER ROLE ${NAILGUN_DB_USER} WITH SUPERUSER LOGIN PASSWORD '${NAILGUN_DB_PW}'"
else
  echo "Creating role ${NAILGUN_DB_USER} with password ${NAILGUN_DB_PASSWD}"
  PGPASSFILE=${NAILGUN_DB_ROOTPGPASS} psql -h 127.0.0.1 -U postgres -c "CREATE ROLE ${NAILGUN_DB_USER} WITH SUPERUSER LOGIN PASSWORD '${NAILGUN_DB_PW}'"
fi

echo "Dropping database ${NAILGUN_DB} if exists"
PGPASSFILE=${NAILGUN_DB_ROOTPGPASS} psql -h 127.0.0.1 -U postgres -c "DROP DATABASE IF EXISTS ${NAILGUN_DB}"
echo "Creating database ${NAILGUN_DB}"
PGPASSFILE=${NAILGUN_DB_ROOTPGPASS} psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE ${NAILGUN_DB} OWNER ${NAILGUN_DB_USER}"
