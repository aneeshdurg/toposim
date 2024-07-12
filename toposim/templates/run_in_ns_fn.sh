run_in_ns() {
  pid=$(docker inspect $1 | jq \.[0].State.Pid)
  shift
  flag="-n"
  # if $1 starts with a -, then replace $flag with $1
  if [[ $1 == -* ]]; then
      flag=$1
      shift
  fi
  sudo nsenter -t $pid $flag "$@"
}
