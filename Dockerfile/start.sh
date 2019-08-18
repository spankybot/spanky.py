#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

docker run -it --rm -v $DIR/..:/botsrc spanky /startup.sh
