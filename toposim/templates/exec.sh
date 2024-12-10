set -e

# Ensure that the hostname is one of the hosts in this config
parse_host() {
  parser=$({
    argparsh new $0 -d "Run a command inside a container" -e "All unparsed arguments are forwarded to the container"
    argparsh add_arg --helptext "Host to execute on" \
    {%- for n in topo.nodes +%}
    -c {{n}} \
    {%- endfor %}
    -- "host"
  })

  eval $(argparsh parse $parser --format shell --local -- "$@")
  echo $host
}

# Get the host from argument 1 and consume the arg
host=$(parse_host $1)
shift

# Execute all remaining arguments on the container
docker exec -it $host "$@"
