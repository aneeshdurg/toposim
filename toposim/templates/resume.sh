# Resume the cluster if paused

{% for n in topo.nodes +%}
docker start {{n}} &
{%- endfor %}

{% for p in topo.ports.values() +%}
docker start {{p.name}} &
{%- endfor %}

wait
sleep 5
./setup-networking
