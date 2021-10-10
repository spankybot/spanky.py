#!/bin/bash

if [[ ! -d /botsrc/.pyenv ]]; then
    git clone https://github.com/pyenv/pyenv.git /botsrc/.pyenv
fi

export PYENV_ROOT="/botsrc/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv init --path)"

pyenv install -s 3.10.0
pyenv global 3.10.0

cd /botsrc/
pip3 install wheel
pip3 install -r requirements.txt

#python3.10 main.py
while true; do python3.10 main.py || sleep 1; done
