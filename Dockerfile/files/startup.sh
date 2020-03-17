#!/bin/bash

if [[ ! -d /botsrc/.pyenv ]]; then
    git clone https://github.com/pyenv/pyenv.git /botsrc/.pyenv
fi

echo 'export PYENV_ROOT="/botsrc/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

pyenv install -s 3.7.1
pyenv shell 3.7.1

cd /botsrc/
pip3 install -r requirements.txt

while true; do python3.5 main.py && sleep 1; done
