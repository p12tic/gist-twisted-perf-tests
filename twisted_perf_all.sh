#!/bin/bash

virtualenv --no-site-packages py27-opt
virtualenv --no-site-packages py27-noopt
virtualenv --no-site-packages --python=/usr/bin/python3 py3-opt
virtualenv --no-site-packages --python=/usr/bin/python3 py3-noopt

TWISTED_OLD=/path/to/old/checkout/of/twisted
TWISTED_NEW=/path/to/new/checkout/of/twisted

. py27-noopt/bin/activate
pip install -U -e "$TWISTED_OLD[dev]"

. py3-noopt/bin/activate
pip install -U -e "$TWISTED_OLD[dev]"

. py27-opt/bin/activate
pip install -U -e "$TWISTED_NEW[dev]"

. py3-opt/bin/activate
pip install -U -e "$TWISTED_NEW[dev]"

. py27-noopt/bin/activate
python twisted_perf_27.py twisted_perf_27_noopt.json

. py27-opt/bin/activate
python twisted_perf_27.py twisted_perf_27_opt.json

. py3-noopt/bin/activate
python twisted_perf.py twisted_perf_36_noopt.json

. py3-opt/bin/activate
python twisted_perf.py twisted_perf_36_opt.json
