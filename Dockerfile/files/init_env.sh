#!/bin/bash
REQ_SIGNATURE="requirements.sha1sum"

# Calculates signature for requirements.txt
calc_signature() {
    echo $(sha1sum 'requirements.txt' | cut -d' ' -f1)
}

# Gets the current requirements.sha1sum signature
get_crt_signature() {
    echo $(cat "$REQ_SIGNATURE")
}

# Calculates the signature file with the current one
update_signature() {
    calc_signature > "$REQ_SIGNATURE"
}


if [[ ! -d /botsrc/.pyenv ]]; then
    git clone https://github.com/pyenv/pyenv.git /botsrc/.pyenv
fi

export PYENV_ROOT="/botsrc/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv init --path)"

pyenv install -s 3.11.4
pyenv global 3.11.4

cd /botsrc/

# Check if we need to install anything new
if [[ $(calc_signature) != $(get_crt_signature) ]];
then
    pip3 install wheel
    pip3 install -r requirements.txt
    update_signature
fi