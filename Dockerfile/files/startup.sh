#!/bin/bash

source /init_env.sh

#python3.10 main.py
while true; do python3.10 main.py || sleep 1; done
