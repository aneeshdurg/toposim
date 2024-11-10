set -e

stats() {
  date
  {%- for n in topo.nodes +%}
  echo -n {{n}} " "
  docker exec -t {{n}} cat /proc/net/dev | awk '/eth0/{print "TX Bytes " $10}'
  {%- endfor %}
}

parser=$({
  argparsh new $0 -d "Get the total number of bytes sent over the network from every node over time"
  argparsh add_arg "file"
})
eval $(argparsh parse $parse -- "$@")

touch $file

while true; do
  echo "" >> $file
  stats >> $file
  sleep 1
done
