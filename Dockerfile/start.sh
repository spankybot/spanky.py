#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

docker run -it --net=host --rm -v $1:/root -v $DIR/..:/botsrc gcplp/spanky:latest /startup.sh
