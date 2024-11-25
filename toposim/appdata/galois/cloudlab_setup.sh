set -e

parser=$({
  argparsh new $0
  argparsh add_arg "toposimdir"
})

eval $(argparsh parse $parser --format assoc_array --name args -- "$@")

pushd ${args["toposimdir"]}
docker build -t galois .
popd
