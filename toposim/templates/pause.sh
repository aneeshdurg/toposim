{%- for node in topo.nodes +%}
docker stop {{node}} &
{%- endfor %}

{%- for p in topo.ports.values() +%}
docker stop {{p.name}} &
{%- endfor %}

wait
