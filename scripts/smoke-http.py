#!/usr/bin/env python3
"""Exercise the compiled program over loopback HTTP; never print capabilities."""
import argparse
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', default='ferry-dock.exe' if os.name == 'nt' else 'ferry-dock')
    args = parser.parse_args()
    binary = Path(args.binary).resolve()
    process = subprocess.Popen([str(binary), '-listen', '127.0.0.1:0', '-ttl', '2s'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding='utf-8')
    output = queue.Queue()
    def capture():
        for line in process.stdout:
            output.put(line)
    threading.Thread(target=capture, daemon=True).start()
    checks = 0
    def check(condition, description):
        nonlocal checks
        if not condition:
            raise AssertionError(description)
        checks += 1
    try:
        deadline = time.monotonic() + 10
        while True:
            line = output.get(timeout=max(.1, deadline - time.monotonic()))
            match = re.search(r'(http://[^\s]+/)#owner=([A-Za-z0-9_-]+)', line)
            if match:
                origin, owner = match.group(1).rstrip('/'), match.group(2)
                break
        def api(method, path, token='', payload=None, extra_headers=None):
            headers = dict(extra_headers or {})
            if token:
                headers['Authorization'] = 'Bearer ' + token
            body = None
            if payload is not None:
                body = json.dumps(payload).encode('utf-8')
                headers['Content-Type'] = 'application/json'
            request = Request(origin + path, data=body, method=method, headers=headers)
            try:
                response = urlopen(request, timeout=5)
            except HTTPError as error:
                response = error
            with response:
                data = response.read()
                return response.status, json.loads(data) if data else None
        check(api('GET', '/healthz')[0] == 200, 'executable readiness')
        status, invite = api('POST', '/api/sessions', owner, {})
        check(status == 201, 'create session')
        sender = parse_qs(urlparse(invite['sendUrl']).fragment)['key'][0]
        route = '/api/sessions/' + invite['id']
        text = '  phone → computer\n渡口 / Ferry Dock\n\t<plain text>  '
        payload = {'idempotencyKey': 'smoke-delivery-1', 'text': text}
        status, receipt = api('POST', route + '/messages', sender, payload)
        check(status == 201 and receipt['text'] == text, 'text fidelity')
        status, duplicate = api('POST', route + '/messages', sender, payload)
        check(status == 200 and duplicate['id'] == receipt['id'], 'retry deduplication')
        status, inbox = api('GET', route + '?after=0', owner)
        check(status == 200 and len(inbox['messages']) == 1 and inbox['messages'][0]['text'] == text,
              'computer retrieval')
        check(api('GET', route, sender)[0] == 401, 'sender cannot read')
        check(api('DELETE', route, sender)[0] == 401, 'sender cannot close')
        check(api('GET', route, owner, extra_headers={'Origin': 'http://untrusted.invalid'})[0] == 403,
              'cross-origin rejection')
        check(api('DELETE', route, owner)[0] == 204, 'owner close')
        check(api('POST', route + '/messages', sender, payload)[0] == 410, 'closed link rejection')
        status, expiring = api('POST', '/api/sessions', owner, {})
        check(status == 201, 'create expiry session')
        time.sleep(2.1)
        check(api('GET', '/api/sessions/' + expiring['id'], owner)[0] == 410, 'expiry rejection')
        print(f'PASS: {checks} compiled-program HTTP checks; loopback only; browser NOT_RUN.')
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()


if __name__ == '__main__':
    main()
