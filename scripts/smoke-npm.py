#!/usr/bin/env python3
"""Exercise a local npm tarball without registry login, publication or GUI.

Uses an existing Node/npm runtime and Python's standard library. npm installs
only the supplied local package with scripts disabled, isolated empty config,
private cache/HOME/prefix and offline mode. Every service belongs to this run.
This is not registry distribution, a phone test, or browser acceptance.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import select
import shutil
import signal
import stat
import subprocess
import tarfile
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen


class Failure(Exception):
    """Messages are fixed labels, never capability-bearing child output."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def package_files(path):
    entries = {}
    total = 0
    with tarfile.open(path, 'r:gz') as archive:
        for item in archive:
            name = item.name.rstrip('/')
            parts = name.split('/')
            if (not name or '\\' in name or name.startswith('/')
                    or parts[0] != 'package' or any(p in ('', '.', '..') for p in parts)):
                raise Failure('npm archive contains an unsafe member name')
            if item.isdir():
                continue
            if not item.isfile() or name in entries:
                raise Failure('npm archive contains a duplicate or non-regular member')
            total += item.size
            if total > 32 << 20 or len(entries) >= 100:
                raise Failure('npm archive exceeds the acceptance bound')
            relative = '/'.join(parts[1:])
            entries[relative] = (archive.extractfile(item).read(), item.mode & 0o777)
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, help='local npm pack .tgz file')
    parser.add_argument('--node', required=True, help='existing supported Node executable')
    parser.add_argument('--npm-cli', required=True, help='existing npm-cli.js, run by --node')
    parser.add_argument('--receipt', default='bin/npm-validation.json')
    options = parser.parse_args()
    archive = Path(options.package).resolve()
    node = Path(options.node).resolve()
    npm_cli = Path(options.npm_cli).resolve()
    receipt_path = Path(options.receipt).resolve()
    checks = []
    processes = []

    def check(value, label):
        if not value:
            raise Failure(label)
        checks.append(label)

    files = package_files(archive)
    check('package.json' in files, 'local tarball contains package metadata')
    metadata = json.loads(files['package.json'][0])
    package_name = metadata['name']
    package_version = metadata['version']
    check(metadata.get('os') == ['darwin'] and metadata.get('cpu') == ['arm64'],
          'package declares only darwin/arm64 support')
    check(not metadata.get('scripts') and not metadata.get('dependencies')
          and not metadata.get('optionalDependencies'),
          'package needs no lifecycle scripts or runtime dependency downloads')
    check(metadata.get('bin', {}).get('ferry-dock') == 'bin/ferry-dock.cjs',
          'package exposes the documented command')
    allow_roots = {'package.json', 'core.json', 'LICENSE', 'README.md',
                   'README.zh-CN.md', 'THIRD_PARTY_NOTICES.md', 'SECURITY.md'}
    allow_prefixes = ('skills/ferry-dock/', 'docs/')
    for name, (data, mode) in files.items():
        check(name in allow_roots or name in ('bin/ferry-dock.cjs', 'native/ferry-dock')
              or name.startswith(allow_prefixes), 'tarball allowlist: ' + name)
        check(not any(p.startswith('.') for p in PurePosixPath(name).parts),
              'tarball contains no dotfiles: ' + name)
        if name != 'native/ferry-dock':
            check(not re.search(rb'(?:npm_[A-Za-z0-9]{36}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|#owner=[A-Za-z0-9_-]{32,})', data),
                  'text artifact has no credential pattern: ' + name)
    check(files['native/ferry-dock'][1] & 0o111 != 0,
          'packed Go executable retains executable mode')
    check(files['bin/ferry-dock.cjs'][1] & 0o111 != 0,
          'packed npm entry retains executable mode')

    with tempfile.TemporaryDirectory(prefix='ferry-dock-npm-check-') as temporary:
        private = Path(temporary)
        prefix = private / '中文 package with spaces'
        prefix.mkdir(mode=0o700)
        home = private / 'home'
        home.mkdir(mode=0o700)
        cache = private / 'cache'
        cache.mkdir(mode=0o700)
        configs = []
        for label in ('user', 'global'):
            config = private / (label + '.npmrc')
            config.touch(mode=0o600)
            configs.append(config)
        environment = {
            'HOME': str(home), 'PATH': str(node.parent) + os.pathsep + '/usr/bin:/bin',
            'TMPDIR': str(private), 'LANG': 'en_US.UTF-8', 'TERM': 'xterm-256color',
            'NPM_CONFIG_USERCONFIG': str(configs[0]),
            'NPM_CONFIG_GLOBALCONFIG': str(configs[1]),
            'NPM_CONFIG_CACHE': str(cache), 'NPM_CONFIG_OFFLINE': 'true',
            'NPM_CONFIG_IGNORE_SCRIPTS': 'true', 'NPM_CONFIG_AUDIT': 'false',
            'NPM_CONFIG_FUND': 'false', 'NPM_CONFIG_UPDATE_NOTIFIER': 'false',
            'NPM_CONFIG_REGISTRY': 'https://registry.npmjs.org/',
        }

        def run(command, label, timeout=20, cwd=prefix, env=environment, success=True):
            try:
                result = subprocess.run([str(p) for p in command], cwd=cwd, env=env,
                                        capture_output=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise Failure(label + ': timed out') from None
            if success:
                check(result.returncode == 0, label)
            return result

        observed = json.loads(run([node, '-p', 'JSON.stringify({node:process.versions.node,os:process.platform,cpu:process.arch})'],
                                  'inspect existing Node runtime').stdout)
        check(int(observed['node'].split('.')[0]) >= 22 and observed['os'] == 'darwin'
              and observed['cpu'] == 'arm64', 'runtime is existing Node 22+ on darwin/arm64')
        npm_version = run([node, npm_cli, '--version'], 'inspect existing npm runtime').stdout.decode().strip()
        npm = [node, npm_cli]
        run(npm + ['install', '--offline', '--ignore-scripts', '--no-audit', '--no-fund',
                   '--package-lock=false', '--prefix', prefix, archive],
            'local offline npm install with scripts disabled', timeout=30)
        installed = prefix / 'node_modules' / package_name
        entry = installed / 'bin/ferry-dock.cjs'
        binary = installed / 'native/ferry-dock'
        check(entry.is_file() and binary.is_file(), 'local package installed under private prefix')
        check(digest(binary.read_bytes()) == digest(files['native/ferry-dock'][0]),
              'installed executable equals packed executable')
        check((prefix / 'node_modules/.bin/ferry-dock').exists(), 'npm created the executable command link')
        repack = private / 'repack'
        repack.mkdir(mode=0o700)
        packed = run(npm + ['pack', installed, '--offline', '--ignore-scripts', '--json',
                            '--pack-destination', repack], 'local npm pack with scripts disabled')
        pack_result = json.loads(packed.stdout)[0]
        repacked = package_files(repack / pack_result['filename'])
        check(set(repacked) == set(files), 'npm repack preserves the exact content allowlist')
        check(all(repacked[name][0] == value[0] for name, value in files.items()),
              'npm repack preserves all packaged file bytes')

        def cli(*args, success=True, timeout=20):
            return run([node, entry, *args], 'wrapper command exit zero',
                       timeout=timeout, success=success)

        result = run(npm + ['exec', '--offline', '--yes=false', '--prefix', prefix,
                            '--', 'ferry-dock', 'version'],
                     'installed npm exec works offline without registry download')
        version = json.loads(result.stdout)
        check(version.get('version') == '0.1.0-alpha.2'
              and version.get('commit') == 'a351555ccd1615795bc2a6c10dd7e97a633a074f',
              'npm execution returns the exact frozen core identity')
        invalid = cli('not-a-command', success=False)
        check(invalid.returncode == 2 and not invalid.stdout,
              'native invalid-command exit code and stdout survive wrapper')
        check(cli('request', 'create', '--help').stdout == b'',
              'help diagnostics do not pollute JSON stdout')

        # VM execution is explicitly a dispatch/guard unit check, not another OS.
        vm_script = private / 'wrapper-vm.cjs'
        vm_script.write_text(r'''const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(process.argv[2], 'utf8');
const dirname = path.dirname(process.argv[2]);
function inspect(platform, arch, nodeVersion, args) {
  let spawned = null, exit = null, stderr = '';
  const stop = new Error('expected VM stop');
  const fake = Object.create(process);
  Object.defineProperties(fake, {
    platform: {value: platform}, arch: {value: arch},
    versions: {value: {...process.versions, node: nodeVersion}},
    version: {value: 'v' + nodeVersion},
    argv: {value: [process.execPath, process.argv[2], ...args]},
    stderr: {value: {write(s) { stderr += s; }}},
    stdout: {value: {write() { throw new Error('unexpected stdout'); }}},
    exit: {value(code) { exit = code; throw stop; }},
    on: {value() { return fake; }}, once: {value() { return fake; }},
    removeListener: {value() { return fake; }}
    ,exitCode: {value: undefined, writable: true}
  });
  function load(name) {
    if (name === 'node:child_process' || name === 'child_process') return {
      spawn(file, argv, options) { spawned = {file, argv, options}; throw stop; }
    };
    return require(name);
  }
  try { vm.runInNewContext(source, {require: load, process: fake, __dirname: dirname,
    __filename: process.argv[2], console, Buffer, setTimeout, clearTimeout}); }
  catch (error) { if (error !== stop) throw error; }
  return {spawned, exit: exit === null ? fake.exitCode : exit, stderr};
}
const defaults = inspect('darwin', 'arm64', process.versions.node, []);
const literal = ['request', 'create', '--prompt', 'literal $(touch NEVER_RUN); 中文'];
const forwarded = inspect('darwin', 'arm64', process.versions.node, literal);
const wrongOS = inspect('linux', 'x64', process.versions.node, ['version']);
const wrongCPU = inspect('darwin', 'x64', process.versions.node, ['version']);
const oldNode = inspect('darwin', 'arm64', '18.0.0', ['version']);
if (!defaults.spawned || JSON.stringify(defaults.spawned.argv) !== '["desktop"]') throw new Error('no-argument dispatch');
if (!forwarded.spawned || JSON.stringify(forwarded.spawned.argv) !== JSON.stringify(literal)) throw new Error('argv forwarding');
if (forwarded.spawned.options.shell !== false || forwarded.spawned.options.stdio !== 'inherit') throw new Error('spawn safety');
if (!path.isAbsolute(forwarded.spawned.file)) throw new Error('binary path');
for (const state of [wrongOS, wrongCPU, oldNode]) if (state.spawned || !state.exit || !state.stderr) throw new Error('guard');
process.stdout.write(JSON.stringify({noArgsToDesktop:true,argvLiteral:true,noShell:true,stdioInherited:true,
  unsupportedOSGuard:true,unsupportedCPUGuard:true,oldNodeGuard:true,scope:'VM only'}));
''')
        vm = json.loads(run([node, vm_script, entry], 'VM no-arg/argv/platform/runtime dispatch guards').stdout)
        check(vm.get('noArgsToDesktop') and vm.get('unsupportedOSGuard')
              and vm.get('unsupportedCPUGuard') and vm.get('oldNodeGuard'),
              'VM guards passed without claiming native other-platform execution')

        for kind in ('missing', 'tampered', 'unexecutable'):
            clone = private / ('package-' + kind)
            shutil.copytree(installed, clone)
            target = clone / 'native/ferry-dock'
            if kind == 'missing':
                target.unlink()
            elif kind == 'tampered':
                with target.open('ab') as stream:
                    stream.write(b'not-the-approved-core')
            else:
                target.chmod(0o600)
            bad = run([node, clone/'bin/ferry-dock.cjs', 'version'], kind+' binary failure',
                      success=False)
            expected = {'missing': 127, 'tampered': 1, 'unexecutable': 126}[kind]
            check(bad.returncode == expected and not bad.stdout and bool(bad.stderr),
                  kind + ' binary is rejected clearly without stdout contamination')

        # Real lifecycle stays isolated, explicitly suppressing the OS browser.
        state_dir = private / 'desktop-state'
        state = None
        try:
            started = json.loads(cli('desktop', '--no-open', '--state-dir', state_dir,
                                     '--listen', '127.0.0.1:0').stdout)
            check(started.get('state') == 'ready' and not started.get('reused'),
                  'real explicit no-GUI desktop starts and launcher returns')
            control = Path(started['controlPath'])
            state = json.loads(control.read_text())

            def api(method, route, token, payload=None):
                body = json.dumps(payload).encode() if payload is not None else None
                request = Request(state['serverUrl']+route, data=body, method=method,
                                  headers={'Authorization': 'Bearer '+token,
                                           'Content-Type': 'application/json'})
                try:
                    response = urlopen(request, timeout=5)
                except HTTPError as error:
                    response = error
                with response:
                    raw = response.read()
                    return response.status, json.loads(raw) if raw else None

            code, info = api('GET', '/api/desktop', state['ownerToken'])
            check(code == 200 and info.get('desktop') is True,
                  'Go service survives npm/Node launcher completion')
            again = cli('desktop', '--no-open', '--state-dir', state_dir,
                        '--listen', '127.0.0.1:0')
            check(json.loads(again.stdout).get('reused') is True,
                  'relaunch reuses the authenticated owned service')
            check(b'reus' in again.stderr.lower() or b'existing' in again.stderr.lower(),
                  'desktop warns that reused service may have a different package version')
            handle = private / '中文 request with spaces.json'
            marker = prefix / 'SHELL_MUST_NOT_RUN'
            prompt = '中文 feedback "quoted" ; $(touch '+str(marker)+') `touch '+str(marker)+'`'
            created = json.loads(cli('request', 'create', '--control', control,
                                     '--task-id', 'npm-literal-task', '--prompt', prompt,
                                     '--handle', handle, '--ttl', '15m', '--max-bytes', '16384').stdout)
            check(created['request']['prompt'] == prompt and not marker.exists(),
                  'real quoted Unicode/shell metacharacter argv remains literal task data')

            def pending():
                return json.loads(cli('request', 'status', '--handle', handle).stdout)['state'] == 'pending'

            for sig in (signal.SIGINT, signal.SIGTERM):
                process = subprocess.Popen([str(node), str(entry), 'request', 'wait',
                                            '--handle', str(handle), '--timeout', '10s'],
                                           cwd=prefix, env=environment, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, start_new_session=True)
                processes.append(process)
                time.sleep(.25)
                process.send_signal(sig)
                output, _ = process.communicate(timeout=15)
                check(process.returncode == 130 and json.loads(output)['error']['code'] == 'wait_canceled',
                      signal.Signals(sig).name+' reaches Go wait and preserves numeric exit 130')
                check(pending(), signal.Signals(sig).name+' interrupts only waiting, not the request')

            # A separate controlling terminal tests terminal-generated Ctrl+C.
            import fcntl
            import termios
            master, slave = os.openpty()
            attrs = termios.tcgetattr(slave)
            attrs[3] = (attrs[3] | termios.ISIG) & ~termios.ECHO
            termios.tcsetattr(slave, termios.TCSANOW, attrs)

            def terminal_child():
                os.setsid()
                fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

            pty_process = None
            try:
                pty_process = subprocess.Popen([str(node), str(entry), 'request', 'wait',
                                                '--handle', str(handle), '--timeout', '10s'],
                                               cwd=prefix, env=environment, stdin=slave,
                                               stdout=slave, stderr=slave, preexec_fn=terminal_child)
                processes.append(pty_process)
                os.close(slave)
                slave = None
                time.sleep(.3)
                os.write(master, b'\x03')
                captured = b''
                deadline = time.monotonic()+15
                while time.monotonic() < deadline:
                    readable, _, _ = select.select([master], [], [], .1)
                    if readable:
                        try:
                            piece = os.read(master, 65536)
                        except OSError as error:
                            if error.errno == errno.EIO:
                                break
                            raise
                        if not piece:
                            break
                        captured += piece
                    elif pty_process.poll() is not None:
                        break
                pty_process.wait(timeout=1)
                rows = [line for line in captured.splitlines() if line.startswith(b'{')]
                check(pty_process.returncode == 130 and rows
                      and json.loads(rows[-1])['error']['code'] == 'wait_canceled',
                      'PTY terminal Ctrl+C forwards once and keeps wait cancellation result')
                check(pending(), 'PTY Ctrl+C leaves request pending')
            finally:
                if slave is not None:
                    os.close(slave)
                os.close(master)

            fragment = parse_qs(urlsplit(created['sendUrl']).fragment)
            text = '  npm phone → same task\n客户：增加两周试点。  '
            code, _ = api('POST', '/api/requests/'+fragment['request'][0]+'/input',
                          fragment['key'][0], {'idempotencyKey':'npm-check-one','text':text})
            check(code == 201, 'synthetic phone submission through npm-created request')
            result = json.loads(cli('request', 'read', '--handle', handle).stdout)
            repeat = json.loads(cli('request', 'read', '--handle', handle).stdout)
            check(result['input']['text'] == text and result['input']['trust'] == 'untrusted_user_input'
                  and result['input']['id'] == repeat['input']['id'],
                  'same npm request reads exact untrusted text with stable repeated input ID')
            code, session = api('POST', '/api/sessions', state['ownerToken'], {})
            check(code == 201, 'ordinary transfer remains available')
            sender = parse_qs(urlsplit(session['sendUrl']).fragment)['key'][0]
            route = '/api/sessions/'+session['id']
            check(api('POST', route+'/messages', sender,
                      {'idempotencyKey':'npm-ordinary-one','text':text})[0] == 201,
                  'ordinary sender accepted while npm entry is installed')
            code, inbox = api('GET', route, state['ownerToken'])
            check(code == 200 and inbox['messages'][0]['text'] == text,
                  'ordinary computer read preserves text')
            check(api('POST', '/api/desktop/quit', state['ownerToken'], {})[0] == 202,
                  'own desktop Quit accepted')
            deadline = time.monotonic()+5
            while control.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            check(not control.exists(), 'own service control file removed after Quit')
            try:
                urlopen(state['serverUrl']+'/healthz', timeout=1)
            except OSError:
                check(True, 'own service socket closed after Quit')
            else:
                raise Failure('owned service remained alive after Quit')
            state = None
        finally:
            if state is not None:
                try:
                    api('POST', '/api/desktop/quit', state['ownerToken'], {})
                except Exception:
                    pass
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)

    receipt = {
        'status': 'PASS_LOCAL', 'packageNameCandidate': package_name,
        'packageVersion': package_version, 'packageFilename': archive.name,
        'packageBytes': archive.stat().st_size, 'packageSha256': digest(archive.read_bytes()),
        'fileCount': len(files), 'files': sorted(files), 'node': observed['node'],
        'npm': npm_version, 'platform': 'darwin/arm64',
        'coreVersion': version, 'checks': checks,
        'scope': 'local npm pack/install/exec only; no registry publish or authentication',
        'notRun': ['public npx/registry installation', 'default no-argument browser opening',
                   'actual other OS/CPU installation or signals', 'Gatekeeper/browser-download first launch',
                   'real browser/clipboard/phone/LAN/QR', 'actual Codex host'],
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status':'PASS_LOCAL','checks':len(checks),'package':package_name,
                      'version':package_version,'bytes':archive.stat().st_size,
                      'scope':receipt['scope'],'receipt':str(receipt_path)},ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (Failure, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        # Do not print subprocess output, request/control objects or capability URLs.
        message = str(error) if isinstance(error, Failure) else type(error).__name__
        print(json.dumps({'status':'FAIL','reason':message}))
        raise SystemExit(1)
