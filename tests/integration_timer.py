"""Real systemd timer test with an isolated journal and zero desktop actions."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import memminning.core as core

with tempfile.TemporaryDirectory(prefix='memminning-timer-test-') as directory:
    core.STATE = Path(directory) / 'memminning'
    store = core.Store(core.STATE)
    backend = core.Backend()
    session = uuid.uuid4().hex
    state = {'schema': 1, 'id': session, 'boot': backend.boot(), 'status': 'active',
             'deadline': time.time() + 3, 'started': time.time(), 'actions': []}
    store.write(state)
    backend.arm(session, 3)
    for _ in range(25):
        if store.read()['status'] == 'restored':
            print('Real systemd timer successfully restored isolated empty session; no desktop targets modified.')
            break
        time.sleep(1)
    else:
        raise SystemExit('Timer recovery did not complete within 25 seconds')
