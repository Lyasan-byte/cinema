#!/bin/bash
set -e

PRIMARY_HOST=$1
REPLICA_NAME=$2
PGDATA=/var/lib/postgresql/data

echo "Starting replica setup for $REPLICA_NAME..."

until pg_isready -h "$PRIMARY_HOST" -p 5432 -U replicator; do
  echo "Waiting for primary..."
  sleep 2
done

rm -rf "${PGDATA:?}"/*

pg_basebackup -h "$PRIMARY_HOST" -D "$PGDATA" -U replicator -P -R

echo "hot_standby = on" >> "$PGDATA/postgresql.conf"
echo "listen_addresses = '*'" >> "$PGDATA/postgresql.conf"

chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"

exec su postgres -c "postgres -D $PGDATA"