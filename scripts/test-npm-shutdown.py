#!/usr/bin/env python3
"""Regress the npm harness's asynchronous owned-service shutdown observation."""
import errno
import importlib.util
import json
import socket
import sys
import time
from pathlib import Path
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import build_opener, ProxyHandler

SPEC = importlib.util.spec_from_file_location('ferry_npm_smoke', Path(__file__).with_name('smoke-npm.py'))
SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMOKE)


class Control:
    def __init__(self, present=False):
        self.present = present

    def exists(self):
        return self.present


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Opener:
    def __init__(self, alive=0, error=None):
        self.alive, self.error, self.calls = alive, error, 0

    def open(self, *args, **kwargs):
        self.calls += 1
        if self.calls <= self.alive:
            return Response()
        if self.error:
            raise self.error
        raise URLError(ConnectionRefusedError(errno.ECONNREFUSED, 'fixture listener closed'))


class ShutdownObservation(unittest.TestCase):
    def test_control_removed_before_listener_closes(self):
        opener = Opener(alive=3)
        self.assertTrue(SMOKE.wait_for_owned_stop(Control(), 'http://127.0.0.1:1', opener, .5))
        self.assertEqual(opener.calls, 4)

    def test_listener_alive_at_deadline_fails(self):
        self.assertFalse(SMOKE.wait_for_owned_stop(Control(), 'http://127.0.0.1:1', Opener(alive=1000), .04))

    def test_retained_control_does_not_pass(self):
        self.assertFalse(SMOKE.wait_for_owned_stop(Control(True), 'http://127.0.0.1:1', Opener(), .04))

    def test_timeout_does_not_prove_socket_closed(self):
        self.assertFalse(SMOKE.wait_for_owned_stop(Control(), 'http://127.0.0.1:1', Opener(error=URLError(TimeoutError('fixture timeout'))), .04))

    def test_http_error_does_not_prove_socket_closed(self):
        failure = HTTPError('http://127.0.0.1:1', 503, 'fixture HTTP failure', {}, None)
        self.assertFalse(SMOKE.wait_for_owned_stop(Control(), 'http://127.0.0.1:1', Opener(error=failure), .04))

    def test_delayed_refusal_needs_more_than_point_three_seconds(self):
        class DelayedRefusal:
            def open(self, *args, timeout, **kwargs):
                if timeout < .35:
                    time.sleep(timeout)
                    raise URLError(TimeoutError('fixture refusal not reported within short budget'))
                time.sleep(.35)
                raise URLError(ConnectionRefusedError(errno.ECONNREFUSED, 'fixture delayed refusal'))
        short = SMOKE.probe_owned_socket('http://127.0.0.1:1', DelayedRefusal(), .3)
        self.assertFalse(short['connectionRefused'])
        self.assertEqual(short['reasonType'], 'TimeoutError')
        self.assertTrue(SMOKE.wait_for_owned_stop(Control(), 'http://127.0.0.1:1', DelayedRefusal(), 1))

    def test_reset_is_not_refused(self):
        failure = URLError(ConnectionResetError(errno.ECONNRESET, 'fixture reset'))
        self.assertFalse(SMOKE.wait_for_owned_stop(Control(), 'http://127.0.0.1:1', Opener(error=failure), .04))

    def test_winsock_refused_socket(self):
        self.assertTrue(SMOKE.wait_for_owned_stop(Control(), 'http://127.0.0.1:1', Opener(error=URLError(OSError(10061, 'fixture Winsock refused'))), .04))


def real_loopback_diagnostic():
    # The port is allocated by this test and immediately closed. No external
    # host, capability, private process or security setting is involved.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    origin = 'http://127.0.0.1:'+str(port)
    opener = build_opener(ProxyHandler({}))
    short = SMOKE.probe_owned_socket(origin, opener, .3)
    portable = SMOKE.probe_owned_socket(origin, opener, 3)
    return {'scope':'OWN_CLOSED_LOOPBACK_PORT', 'platform':sys.platform,
            'shortBudget':short, 'portableBudget':portable}


if __name__ == '__main__':
    diagnostic = real_loopback_diagnostic()
    print(json.dumps({'shutdownProbeDiagnostic':diagnostic}), flush=True)
    result = unittest.main(exit=False)
    if not result.result.wasSuccessful() or not diagnostic['portableBudget']['connectionRefused']:
        raise SystemExit(1)
