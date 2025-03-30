#!/bin/sh
#
# This script is used to run your program on CodeCrafters
#
# This runs after .codecrafters/compile.sh
#
# Learn more: https://codecrafters.io/program-interface

# HACK Removing pipenv here changes python3 startup time from 700ms to almost nothing 
exec python3 -m app.main "$@"
