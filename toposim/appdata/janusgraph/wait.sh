while [ ! -e /etc/cassandra/done ]; do
  sleep 1;
done;

./docker-entrypoint.sh
