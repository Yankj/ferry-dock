#!/usr/bin/env python3
"""Regress the npm harness's asynchronous owned-service shutdown observation."""
import errno
import importlib.util
from pathlib import Path
import unittest
from urllib.error import HTTPError, URLError

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

    def test_winsock_refused_socket(self):
        self.assertTrue(SMOKE.wait_for_owned_stop(Control(), 'http://127.0.0.1:1', Opener(error=URLError(OSError(10061, 'fixture Winsock refused'))), .04))


if __name__ == '__main__':
    unittest.main()
