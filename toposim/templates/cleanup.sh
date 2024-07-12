# Delete all docker state for this cluster

cleanup() {
    docker stop $1
    docker rm $1
}

{% for p in topo.ports.values() +%}
cleanup {{p.name}} &
{%- endfor %}

{% for n in topo.nodes +%}
cleanup {{n}} &
{%- endfor %}

wait

{% for net in topo.networks +%}
{%- set net_name = topo.prefix + "_" + net.name %}
{%- set net_name = net_name.lower() %}
docker network rm {{net_name}}
{%- endfor %}
