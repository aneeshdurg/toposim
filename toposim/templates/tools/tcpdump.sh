{% include 'run_in_ns_fn.sh' %}

start_tcpdump() {
  local output_dir="$1"

{%- for n in topo.nodes +%}
  output_file=$output_dir/{{n}}_eth0
  run_in_ns {{n}} tcpdump -e -i eth0 -w $output_file &
{%- endfor %}


{%- for p in topo.ports.values() +%}
  {%- for i in range(p.networks | length) +%}

  output_file=$output_dir/{{p.name}}_eth{{i}}
  run_in_ns {{p.name}} tcpdump -e -i eth{{i}} -w $output_file &
  {%- endfor %}
{%- endfor %}
}

stop_tcpdump() {
  # This will kill ALL tcpdump processes - so make sure you're not running any
  # tcpdump instances that weren't started by this script.
  # TODO - only kill process started by this script
  sudo pkill tcpdump
}

usage() {
    echo "Usage: $0 {start|stop} [output directory]"
    exit 1
}
sudo true

# Main script logic
case "$1" in
  start)
    [ $# -eq 2 ] || usage
    start_tcpdump
    ;;
  stop)
    stop_tcpdump
    ;;
  *)
    usage
    ;;
esac
