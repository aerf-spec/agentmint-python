#!/bin/bash
# Independent verification of this evidence bundle.
# python3 + pynacl.  No Blue Magma dashboard required.
set -e
cd "$(dirname "$0")"
exec python3 verify.py
