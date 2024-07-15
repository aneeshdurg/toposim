stats() {
  date
  {%- for n in topo.nodes +%}
  echo -n {{n}} " "
  docker exec -t {{n}} cat /proc/net/dev | awk '/eth0/{print "TX Bytes " $10}'
  {%- endfor %}
}

usage() {
  echo 'Get the total number of bytes sent over the network from every node'
  echo 'over time'
  echo 'Usage: ./tools/egress <output filename>'
  exit 1
}

set -e

if [ $# != 1 ]; then
  usage >&2
fi

file=$1

touch $file

while true; do
  echo "" >> $file
  stats >> $file
  sleep 1
done
