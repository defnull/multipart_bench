#!/bin/bash
python3 -mvenv venv
. venv/bin/activate

pip install -U pip tabulate matplotlib numpy
pip install werkzeug

# The "python-multipart" package installs itself as just "multipart", causing a
# name conflict with multipart.py. For this benchmark we can simply rename it,
# but for actual applications this may be a real issue if some dependency pulls
# in "python-multipart" and breaks "multipart".
pip install python-multipart
pushd venv/lib/python3.*/site-packages/
  mv multipart python_multipart
  mv multipart.dist-info python_multipart.dist-info
popd

pip install multipart