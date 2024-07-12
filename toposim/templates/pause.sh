# Pause the cluster. use ./resume to bring it back online
# (or use docker compose up -d to bring it up without networking)

{%- for node in topo.nodes +%}
docker stop {{node}} &
{%- endfor %}

{%- for p in topo.ports.values() +%}
docker stop {{p.name}} &
{%- endfor %}

wait
