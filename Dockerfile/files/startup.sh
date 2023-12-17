#!/bin/bash

source /init_env.sh

while true; do python3.11 main.py || sleep 1; done
