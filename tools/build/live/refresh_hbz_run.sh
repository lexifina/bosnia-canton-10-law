#!/bin/bash
# Supervisor entry for refresh_hbz.sh (runners.json): writes the status file runner_supervisor reads, so a run that
# failed a gate (exit 1) is left stopped and reported instead of being restarted in a loop.
SRC=/c/Users/alany/Documents/bosnia-canton-10-law-src
st() { python -X utf8 -c "import json,sys,datetime as d;json.dump({'state':sys.argv[1],'last_error':sys.argv[2],'updated':d.datetime.now(d.timezone.utc).isoformat(timespec='seconds')},open(sys.argv[3],'w'))" "$1" "$2" "$(cygpath -m $SRC)/refresh-status.json"; }
st running ""
bash /c/Users/alany/Documents/lexifina/scripts/bosnia-canton-10-law/live/refresh_hbz.sh
rc=$?
if [ $rc -ne 0 ]; then st stopped "exit $rc: $(tail -n 1 $SRC/refresh.log | cut -c1-300)"; else st stopped "stop file or once"; fi
exit $rc
