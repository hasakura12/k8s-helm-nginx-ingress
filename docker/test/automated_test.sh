#!/bin/sh
CWD="$(cd "$(dirname "$0")" && pwd)" # Script directory
pushd "${CWD}" >/dev/null

set -o errexit  # Exit if a command fails
set -o pipefail # Exit if one command in a pipeline fails
set -o nounset  # Treat  unset  variables and parameters as errors
set -o xtrace   # Print a trace of simple commands

# Function: print usage
function usage {
	>&2 echo "
    What is this:
    A script to run Python BDD tests using "behave" against a Nginx docker container.

    Usage:
    ./automated_test.sh
    $0
  "
}

function main() {
    ## Start a container which executes python tests internally
    docker-compose up --build
}

main "$@"
