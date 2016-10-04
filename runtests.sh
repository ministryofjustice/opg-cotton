#!/usr/bin/env bash
WORKSPACE=`pwd`
PATH=$WORKSPACE/venv/bin:/usr/local/bin:$PATH

find . -type f -name '*.pyc' -exec rm {} +

if [ ! -d "venv" ]; then
  virtualenv venv
fi

. venv/bin/activate

# update setup tools to a later version
pip install -U pip wheel setuptools
pip install --upgrade -r requirements.txt
pip install --upgrade -r test-requirements.txt

make test
