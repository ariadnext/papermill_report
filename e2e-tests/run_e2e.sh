#!/bin/bash
set -e

python3 -m pip install -r ./requirements_e2e.txt
# Ensure files written by playwright on the volume are writable by everybody
umask a+w
# End to end tests are stored in a separate folder
# so that pytest does not try to import dependencies of papermill_report
# Therefore the image controlling the frontend actions only requires playwright stack
python3 -m pytest -m e2e ./e2e-tests/test_integration.py --base-url http://hub:8000
