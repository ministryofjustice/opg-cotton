#!/usr/bin/env bash
WORKSPACE=`pwd`
PATH=$WORKSPACE/venv/bin:/usr/local/bin:$PATH

if [ ! -d "venv" ]; then
  virtualenv venv
fi

. venv/bin/activate

# update setup tools to a later version
pip install -U pip wheel setuptools
pip install -r requirements.txt
pip install -r test-requirements.txt

make test
