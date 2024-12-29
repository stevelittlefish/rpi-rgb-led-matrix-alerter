#!/bin/bash
cd "$(dirname "$0")/alerter"
python ./alerter.py $*
