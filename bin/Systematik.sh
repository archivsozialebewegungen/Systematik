#!/bin/bash

DB_URL=postgresql://archivar:archivar@mossmann2:5432/archiv
export DB_URL

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

source $DIR/../venv/bin/activate
export PYTHONPATH=$DIR/../src:$PYTHONPATH
python3 $DIR/../src/asb/systematik/SystematikGui.py