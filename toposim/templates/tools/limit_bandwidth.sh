# Usage ./tools/limit_bandwidth.sh <bandwidth>
#   if bandwidth is not supplied, then the default will be 1024
bandwidth=${1:-1024}

{% include 'run_in_ns_fn.sh' %}

# Check if the interface ifb0 exists in container $1
ifb_exists() {
  run_in_ns $1 ip link | grep ifb0 > /dev/null
}

# Install the ifb0 interface in container $1 if it doesn't exist
install_ifb() {
  if ! ifb_exists $1; then
    run_in_ns $1 ip link add ifb0 type ifb
    run_in_ns $1 ip link set dev ifb0 up
  fi
}

{%- for n in topo.nodes +%}
install_ifb {{n}} &
{%- endfor %}
wait

# clear existing limit if set
{%- for n in topo.nodes +%}
run_in_ns {{n}} wondershaper -a eth0 -c &
{%- endfor %}
wait

# set limit
{%- for n in topo.nodes +%}
run_in_ns {{n}} wondershaper -a eth0 -d $bandwidth -u $bandwidth &
{%- endfor %}
wait
