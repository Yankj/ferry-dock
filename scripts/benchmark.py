#!/usr/bin/env python3
"""Measure a compiled Ferry Dock process over loopback HTTP (stdlib only).

No capability, request ID, submitted text, or response body is written to results.
Use --calibration explicitly for short harness checks; those are not baselines.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import platform
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import parse_qs, urlparse
import uuid

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ('Ferry Dock synthetic benchmark text. ' + 'x' * 1024)[:1024]
OWNER_LINK = re.compile(r'(http://127\.0\.0\.1:\d+)/#owner=([A-Za-z0-9_-]+)')


def command_output(argv):
    try:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                                timeout=10, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def summary(values):
    if not values:
        return {'count': 0}
    ordered = sorted(values)
    def percentile(p):
        return ordered[max(0, math.ceil(p * len(ordered)) - 1)]
    return {'count': len(values), 'min_ms': ordered[0],
            'p50_ms': percentile(.50), 'p95_ms': percentile(.95),
            'p99_ms': percentile(.99), 'max_ms': ordered[-1]}


def progress(message):
    print(message, flush=True)


class BenchmarkError(RuntimeError):
    pass


class Client:
    """One persistent connection per client; latency excludes JSON decoding."""
    def __init__(self, origin, errors):
        self.origin = origin
        parsed = urlparse(origin)
        self.connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=15)
        self.errors = errors
        self.last_status = None

    def call(self, method, path, token='', payload=None, expected=(200,), label='HTTP', on_sent=None):
        headers = {}
        body = None
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if payload is not None:
            headers['Content-Type'] = 'application/json'
            body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        started = time.perf_counter_ns()
        self.connection.request(method, path, body=body, headers=headers)
        if on_sent:
            on_sent()
        response = self.connection.getresponse()
        self.last_status = response.status
        data = response.read()
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        parsed = json.loads(data) if data else None
        if response.status not in expected:
            code = parsed.get('code', '') if isinstance(parsed, dict) else ''
            code = re.sub(r'[^a-zA-Z0-9_-]', '', str(code))[:64]
            self.errors.append({'operation': label, 'status': response.status, 'code': code})
            raise BenchmarkError(f'{label} returned HTTP {response.status}')
        return parsed, elapsed_ms

    def close(self):
        self.connection.close()


class Runtime:
    """Own only the benchmark child process; never scan or stop other processes."""
    def __init__(self, binary, errors):
        self.binary = binary
        self.errors = errors
        self.process = None
        self.origin = None
        self.owner = None
        self.startup_ms = None
        self.readers = []

    def __enter__(self):
        started = time.perf_counter_ns()
        self.process = subprocess.Popen(
            [str(self.binary), '-listen', '127.0.0.1:0', '-ttl', '15m'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        lines = queue.Queue(maxsize=32)
        def capture():
            for line in self.process.stdout:
                try:
                    lines.put_nowait(line)
                except queue.Full:
                    pass
        def discard_errors():
            for _ in self.process.stderr:
                pass
        self.readers = [threading.Thread(target=capture, daemon=True),
                        threading.Thread(target=discard_errors, daemon=True)]
        for reader in self.readers:
            reader.start()
        deadline = time.monotonic() + 10
        try:
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise BenchmarkError(f'benchmark server exited with code {self.process.returncode}')
                try:
                    line = lines.get(timeout=.05)
                except queue.Empty:
                    continue
                match = OWNER_LINK.search(line)
                if match:
                    self.origin, self.owner = match.groups()
                    client = self.client()
                    try:
                        data, _ = client.call('GET', '/healthz', label='readiness')
                        if data != {'status': 'ok'}:
                            raise BenchmarkError('unexpected readiness response')
                    finally:
                        client.close()
                    self.startup_ms = (time.perf_counter_ns() - started) / 1_000_000
                    return self
            raise BenchmarkError('server readiness timed out after 10 seconds')
        except BaseException:
            self.stop()
            raise

    def client(self):
        return Client(self.origin, self.errors)

    def stop(self):
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        for reader in self.readers:
            reader.join(timeout=1)
        self.process.stdout.close()
        self.process.stderr.close()

    def __exit__(self, *_):
        self.stop()


class RSSSampler:
    """ps RSS is KiB on macOS/Linux. Peak is sampled, not an OS high-water mark."""
    def __init__(self, pid):
        self.pid = pid
        self.started = time.monotonic()
        self.samples = []
        self.unavailable = None
        self.done = threading.Event()
        self.lock = threading.Lock()
        self.thread = None

    def sample(self):
        if self.unavailable:
            return None
        try:
            result = subprocess.run(['ps', '-o', 'rss=', '-p', str(self.pid)],
                                    capture_output=True, text=True, timeout=2, check=True)
            value = int(result.stdout.strip())
            sample = {'elapsed_s': time.monotonic() - self.started, 'rss_kib': value}
            with self.lock:
                self.samples.append(sample)
            return sample
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            self.unavailable = type(error).__name__ + ': RSS for the owned child PID unavailable'
            return None

    def start(self):
        self.sample()
        def run():
            while not self.done.wait(.25):
                if self.sample() is None:
                    return
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.done.set()
        if self.thread:
            self.thread.join(timeout=3)


def create_session(client, owner):
    invitation, _ = client.call('POST', '/api/sessions', owner, {}, (201,), 'session create')
    sender = parse_qs(urlparse(invitation['sendUrl']).fragment)['key'][0]
    return '/api/sessions/' + invitation['id'], sender


def session_load(runtime, cycles, clients):
    """Create/rotate independent inboxes so successful workloads never hit quotas."""
    started = []
    barrier = threading.Barrier(clients, action=lambda: started.append(time.perf_counter()))
    def worker(worker_id):
        count = cycles // clients + (worker_id < cycles % clients)
        client = runtime.client()
        route = sender = None
        submit_ms, read_ms = [], []
        cursor = 0
        in_session = 0
        try:
            route, sender = create_session(client, runtime.owner)
            def cycle(measured):
                nonlocal route, sender, cursor, in_session
                if in_session >= 120:
                    client.call('DELETE', route, runtime.owner, expected=(204,), label='session rotate close')
                    route, sender = create_session(client, runtime.owner)
                    cursor = in_session = 0
                payload = {'idempotencyKey': uuid.uuid4().hex, 'text': PAYLOAD}
                receipt, post_time = client.call('POST', route + '/messages', sender, payload,
                                                 (201,), 'session submit')
                inbox, get_time = client.call('GET', route + '?after=' + str(cursor), runtime.owner,
                                              label='session incremental read')
                if len(inbox['messages']) != 1 or inbox['messages'][0]['id'] != receipt['id'] or inbox['messages'][0]['text'] != PAYLOAD:
                    raise BenchmarkError('session correctness check failed')
                cursor = inbox['nextCursor']
                in_session += 1
                if measured:
                    submit_ms.append(post_time)
                    read_ms.append(get_time)
            for _ in range(5):
                cycle(False)
            barrier.wait(timeout=15)
            for _ in range(count):
                cycle(True)
            return submit_ms, read_ms
        finally:
            if route:
                client.call('DELETE', route, runtime.owner, expected=(204,), label='session cleanup')
            client.close()
    submit_ms, read_ms = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=clients) as pool:
        for posts, reads in pool.map(worker, range(clients)):
            submit_ms.extend(posts)
            read_ms.extend(reads)
    elapsed = time.perf_counter() - started[0]
    return {'clients': clients, 'payload_utf8_bytes': len(PAYLOAD.encode()),
            'cycles': cycles, 'wall_seconds_including_rotation_and_cleanup': elapsed,
            'successful_operations_per_second': (len(submit_ms) + len(read_ms)) / elapsed,
            'submit': summary(submit_ms), 'read': summary(read_ms),
            'submit_raw_ms': submit_ms, 'read_raw_ms': read_ms}


def create_request(client, owner, index):
    created, elapsed = client.call('POST', '/api/requests', owner,
                                  {'taskId': 'benchmark', 'prompt': f'Synthetic feedback {index}'},
                                  (201,), 'request create with QR')
    route = '/api/requests/' + created['request']['requestId']
    sender = parse_qs(urlparse(created['sendUrl']).fragment)['key'][0]
    return created, route, sender, elapsed


def request_load(runtime, samples):
    client = runtime.client()
    create_ms, submit_ms, read_ms = [], [], []
    try:
        for index in range(samples):
            created, route, sender, create_time = create_request(client, runtime.owner, index)
            reader = created['readerToken']
            receipt, submit_time = client.call('POST', route + '/input', sender,
                                               {'idempotencyKey': uuid.uuid4().hex, 'text': PAYLOAD},
                                               (201,), 'request submit')
            result, read_time = client.call('GET', route + '/result', reader, label='request read')
            value = result.get('input')
            if not value or value['text'] != PAYLOAD or value['trust'] != 'untrusted_user_input' or value['id'] != receipt['id']:
                raise BenchmarkError('request correctness check failed')
            client.call('DELETE', route, reader, label='request cleanup')
            create_ms.append(create_time)
            submit_ms.append(submit_time)
            read_ms.append(read_time)
    finally:
        client.close()
    return {'samples': samples, 'payload_utf8_bytes': len(PAYLOAD.encode()),
            'create_with_qr': summary(create_ms), 'submit': summary(submit_ms), 'read': summary(read_ms),
            'create_with_qr_raw_ms': create_ms, 'submit_raw_ms': submit_ms, 'read_raw_ms': read_ms}


def wait_pressure(runtime, cycles, clients, waiters):
    control = runtime.client()
    pending = []
    submitted = threading.Barrier(waiters + 1)
    sent = [threading.Event() for _ in range(waiters)]
    def wait_one(route, reader, index):
        client = runtime.client()
        try:
            submitted.wait(timeout=15)
            result, elapsed = client.call('GET', route + '/wait?timeoutMs=10000', reader,
                                          label='pending request wait', on_sent=sent[index].set)
            if result['timedOut'] or result['request']['state'] != 'canceled':
                raise BenchmarkError('waiters did not remain pending throughout the text workload')
            return elapsed
        finally:
            client.close()
    try:
        for index in range(waiters):
            created, route, _, _ = create_request(control, runtime.owner, 'wait-' + str(index))
            pending.append((route, created['readerToken']))
        with concurrent.futures.ThreadPoolExecutor(max_workers=waiters) as pool:
            futures = [pool.submit(wait_one, route, reader, index)
                       for index, (route, reader) in enumerate(pending)]
            submitted.wait(timeout=15)
            for event in sent:
                if not event.wait(timeout=2):
                    raise BenchmarkError('wait request dispatch timed out')
            # Give the server time to admit all dispatched requests. With all
            # eight slots occupied, a ninth 1 ms wait must fail immediately.
            time.sleep(.1)
            capacity_confirmed = False
            capacity_probe_status = None
            try:
                if waiters == 8:
                    probe, _ = control.call('GET', pending[0][0] + '/wait?timeoutMs=1',
                                             pending[0][1], expected=(200, 429),
                                             label='expected wait-capacity probe')
                    capacity_probe_status = control.last_status
                    capacity_confirmed = capacity_probe_status == 429 and probe.get('code') == 'capacity'
                    if not capacity_confirmed:
                        raise BenchmarkError('could not confirm all eight wait slots occupied')
                result = session_load(runtime, cycles, clients)
            finally:
                for route, reader in pending:
                    control.call('DELETE', route, reader, label='wait pressure cleanup')
            waits = [future.result(timeout=12) for future in futures]
        result['pending_waiters'] = waiters
        result['all_eight_wait_slots_confirmed_by_capacity_probe'] = capacity_confirmed
        result['expected_capacity_probe_http_status'] = capacity_probe_status
        result['wait_completion_raw_ms'] = waits
        result['waits_explicitly_canceled_after_text_workload'] = True
        return result
    finally:
        control.close()


def full_session_memory(runtime, rss):
    client = runtime.client()
    routes = []
    text = 'x' * 65536
    try:
        before = rss.sample()
        for _ in range(16):
            route, sender = create_session(client, runtime.owner)
            routes.append(route)
            for _ in range(16):
                receipt, _ = client.call('POST', route + '/messages', sender,
                                         {'idempotencyKey': uuid.uuid4().hex, 'text': text},
                                         (201,), 'capacity fill submit')
                if len(receipt['text']) != 65536:
                    raise BenchmarkError('capacity fill text was not preserved')
        time.sleep(.5)
        full = rss.sample()
    finally:
        for route in routes:
            client.call('DELETE', route, runtime.owner, expected=(204,), label='capacity cleanup')
        client.close()
    time.sleep(.5)
    return {'sessions': 16, 'messages_per_session': 16, 'retained_text_bytes': 16 * 1024 * 1024,
            'before_fill': before, 'at_capacity': full, 'after_close': rss.sample()}


def metadata(binary, args):
    digest = hashlib.sha256()
    with binary.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    go = args.go or shutil.which('go')
    build_info = command_output([go, 'version', '-m', str(binary)]) if go else None
    if build_info:
        build_info = build_info.replace(str(binary), '<binary>')
    memory = command_output(['sysctl', '-n', 'hw.memsize']) if sys.platform == 'darwin' else None
    cpu = command_output(['sysctl', '-n', 'machdep.cpu.brand_string']) if sys.platform == 'darwin' else platform.processor()
    dirty = command_output(['git', 'status', '--porcelain'])
    revision = re.search(r'(?m)^\s*build\s+vcs\.revision=(\S+)$', build_info or '')
    modified = re.search(r'(?m)^\s*build\s+vcs\.modified=(true|false)$', build_info or '')
    return {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'os': platform.system(), 'os_release': platform.release(), 'architecture': platform.machine(),
            'cpu': cpu, 'logical_cpus': os.cpu_count(), 'physical_memory_bytes': int(memory) if memory else None,
            'power_mode': 'not recorded', 'background_load': 'not controlled; record an otherwise quiet run',
            'binary_name': binary.name, 'binary_bytes': binary.stat().st_size,
            'binary_sha256': digest.hexdigest(), 'go_build_info': build_info,
            'binary_source_revision': revision.group(1) if revision else None,
            'binary_source_modified': modified.group(1) == 'true' if modified else None,
            'working_tree_commit': command_output(['git', 'rev-parse', 'HEAD']),
            'working_tree_dirty': None if dirty is None else bool(dirty),
            'build_command_recorded_by_caller': args.build_command,
            'runtime_environment': {key: os.environ[key] for key in ('GOMAXPROCS', 'GOMEMLIMIT', 'GODEBUG') if key in os.environ},
            'calibration_only': args.calibration}


def save(path, result):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
        temporary = handle.name
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'bin/perf-results/baseline.json')
    parser.add_argument('--go', help='optional Go executable used only to read binary build metadata')
    parser.add_argument('--build-command', default='not supplied')
    parser.add_argument('--startup-samples', type=int, default=100)
    parser.add_argument('--idle-seconds', type=float, default=60)
    parser.add_argument('--cycles', type=int, default=1000, help='successful session submit/read pairs per phase')
    parser.add_argument('--clients', type=int, default=10)
    parser.add_argument('--request-samples', type=int, default=32)
    parser.add_argument('--waiters', type=int, default=8)
    parser.add_argument('--skip-requests', action='store_true', help='explicit pre-request-version comparison only')
    parser.add_argument('--skip-capacity', action='store_true')
    parser.add_argument('--allow-missing-rss', action='store_true')
    parser.add_argument('--calibration', action='store_true', help='mark short harness checks as non-baseline')
    args = parser.parse_args()
    if not args.binary.is_file():
        parser.error('--binary must name an existing compiled executable')
    if not (1 <= args.clients <= 10 and args.cycles >= args.clients and 1 <= args.waiters <= 8 and 1 <= args.request_samples <= 56):
        parser.error('clients 1..10, cycles >= clients, waiters 1..8, request-samples 1..56 are required')
    if args.request_samples + args.waiters > 64:
        parser.error('request samples plus waiters must fit 64 retained records')
    if args.startup_samples < 1 or args.idle_seconds < 0:
        parser.error('startup-samples must be positive and idle-seconds nonnegative')
    if not args.calibration and (args.startup_samples < 30 or args.idle_seconds < 60):
        parser.error('a baseline needs >=30 startup samples and >=60 idle seconds; use --calibration for short checks')
    binary = args.binary.resolve()
    if args.calibration:
        progress('CALIBRATION ONLY: short harness check; no performance baseline is being established')
    errors = []
    result = {'schema_version': 1, 'environment': metadata(binary, args), 'unexpected_http_errors': errors,
              'method': {'transport': 'loopback HTTP/1.1, one persistent connection per client',
                         'latency': 'request send through response body read; client JSON decoding excluded',
                         'percentiles': 'nearest rank; not confidence intervals',
                         'startup': 'fresh process to successful health response, warm OS filesystem caches',
                         'rss': 'owned child PID only; ps KiB, sampled every 250ms; sampled peak is not true high-water mark',
                         'browser_and_real_device': 'NOT_RUN'}, 'phases': {}}
    rss = None
    try:
        startup = []
        for index in range(args.startup_samples):
            with Runtime(binary, errors) as runtime:
                startup.append(runtime.startup_ms)
            if (index + 1) % 20 == 0:
                progress(f'startup: {index + 1}/{args.startup_samples}')
        result['phases']['startup'] = {**summary(startup), 'raw_ms': startup}
        progress('sampling idle RSS before creating sessions')
        with Runtime(binary, errors) as runtime:
            rss = RSSSampler(runtime.process.pid).start()
            idle_started = time.monotonic()
            last_report = 0
            while time.monotonic() - idle_started < args.idle_seconds:
                elapsed = time.monotonic() - idle_started
                if int(elapsed) // 15 > last_report:
                    last_report = int(elapsed) // 15
                    progress(f'idle sampling: {int(elapsed)}/{int(args.idle_seconds)} seconds')
                time.sleep(min(1, max(0, args.idle_seconds - elapsed)))
            settled = rss.sample()
            result['phases']['idle'] = {'duration_seconds': time.monotonic() - idle_started,
                                       'initial_sample': rss.samples[0] if rss.samples else None,
                                       'settled_sample': settled}
            if rss.unavailable and not args.allow_missing_rss:
                raise BenchmarkError(rss.unavailable)
            progress('measuring successful 1 KiB text cycles')
            result['phases']['ordinary_text'] = session_load(runtime, args.cycles, args.clients)
            if args.skip_requests:
                result['phases']['request_text'] = {'status': 'NOT_RUN', 'reason': '--skip-requests'}
                result['phases']['text_with_pending_waits'] = {'status': 'NOT_RUN', 'reason': '--skip-requests'}
            else:
                progress('measuring request creation, input and read separately')
                result['phases']['request_text'] = request_load(runtime, args.request_samples)
                progress('measuring ordinary text with pending request waits')
                result['phases']['text_with_pending_waits'] = wait_pressure(runtime, args.cycles, args.clients, args.waiters)
            if not args.skip_capacity:
                progress('measuring sampled RSS at the ordinary session text quota')
                result['phases']['session_capacity'] = full_session_memory(runtime, rss)
            else:
                result['phases']['session_capacity'] = {'status': 'NOT_RUN', 'reason': '--skip-capacity'}
            rss.stop()
            result['rss'] = {'samples': rss.samples, 'unavailable_reason': rss.unavailable,
                             'sampled_peak_kib': max((sample['rss_kib'] for sample in rss.samples), default=None)}
        final_digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        result['binary_sha256_after_run'] = final_digest
        if final_digest != result['environment']['binary_sha256']:
            raise BenchmarkError('binary changed while the benchmark was running')
        result['status'] = 'success'
    except BaseException as error:
        if rss:
            rss.stop()
            result['rss'] = {'samples': rss.samples, 'unavailable_reason': rss.unavailable}
        result['status'] = 'failure'
        result['failure'] = {'type': type(error).__name__, 'message': str(error)}
        save(args.output, result)
        progress(f'Benchmark failed; raw result saved to {args.output}')
        raise
    save(args.output, result)
    progress(f'{"Calibration" if args.calibration else "Benchmark"} complete; raw result saved to {args.output}')
    if args.calibration:
        return
    for name, phase in result['phases'].items():
        if name == 'startup':
            progress(f'startup p95: {phase["p95_ms"]:.3f} ms ({phase["count"]} samples)')
        elif 'submit' in phase:
            progress(f'{name} submit/read p95: {phase["submit"]["p95_ms"]:.3f}/{phase["read"]["p95_ms"]:.3f} ms')


if __name__ == '__main__':
    main()
