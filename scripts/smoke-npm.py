#!/usr/bin/env python3
"""Native acceptance of seven local npm tarballs, offline and scripts disabled.

No registry writes/login, browser, phone or global configuration. Actual foreign
platforms are not executed; VM checks are explicitly labeled dispatch simulation.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import errno
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen, build_opener, ProxyHandler

class Failure(Exception):
    pass

def digest(data):
    return hashlib.sha256(data).hexdigest()

def package_files(path):
    entries, total = {}, 0
    with tarfile.open(path, 'r:gz') as archive:
        for item in archive:
            name = item.name.rstrip('/')
            parts = name.split('/')
            if not name or '\\' in name or name.startswith('/') or parts[0] != 'package' or any(p in ('','.','..') for p in parts):
                raise Failure('unsafe npm archive member')
            if item.isdir():
                continue
            relative = '/'.join(parts[1:])
            if not item.isfile() or relative in entries:
                raise Failure('duplicate or nonregular npm member')
            total += item.size
            if total > 32 << 20 or len(entries) >= 100:
                raise Failure('npm archive exceeds acceptance bound')
            entries[relative] = (archive.extractfile(item).read(), item.mode & 0o777)
    return entries

@contextmanager
def private_directory():
    directory = Path(tempfile.mkdtemp(prefix='ferry-dock-npm-check-'))
    cleanup = {'preserve':False}
    try:
        yield directory,cleanup
    finally:
        if not cleanup['preserve']:
            shutil.rmtree(directory)

def probe_owned_socket(origin, opener, timeout):
    """Return only capability-free evidence; an HTTP error is an open socket."""
    started = time.monotonic()
    observation = {'connectionRefused':False, 'errorType':None, 'reasonType':None,
                   'errno':None, 'winerror':None, 'probeTimeoutMs':round(timeout*1000)}
    try:
        with opener.open(origin+'/healthz', timeout=timeout):
            pass
    except OSError as error:
        reason = getattr(error, 'reason', error)
        observation.update({'errorType':type(error).__name__, 'reasonType':type(reason).__name__,
                            'errno':getattr(reason, 'errno', None), 'winerror':getattr(reason, 'winerror', None)})
        observation['connectionRefused'] = (isinstance(reason, ConnectionRefusedError)
            or observation['errno'] in (errno.ECONNREFUSED, 10061)
            or observation['winerror'] == 10061)
    observation['probeElapsedMs'] = round((time.monotonic()-started)*1000)
    return observation


def wait_for_owned_stop(control, origin, opener, timeout=5, observations=None):
    """202 is asynchronous: require absent control and explicitly refused socket.

    Give a refused connection enough time to be reported by the platform, while
    preserving the total deadline. Timeouts, resets and HTTP errors never pass.
    """
    started = time.monotonic()
    deadline = started+timeout
    attempts = 0
    while time.monotonic() < deadline:
        attempts += 1
        observation = probe_owned_socket(origin, opener, min(3, max(.001, deadline-time.monotonic())))
        observation.update({'controlPresent':control.exists(), 'attempts':attempts,
                            'totalElapsedMs':round((time.monotonic()-started)*1000)})
        if observations is not None:
            observations.clear()
            observations.update(observation)
        if observation['connectionRefused'] and not observation['controlPresent']:
            return True
        time.sleep(min(.02, max(0, deadline-time.monotonic())))
    return False

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', required=True, type=Path)
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--npm-cli', type=Path)
    parser.add_argument('--receipt', default='bin/npm-validation.json', type=Path)
    options = parser.parse_args()
    node = Path(options.node).resolve()
    if options.npm_cli is None:
        candidates = [node.parent/'node_modules/npm/bin/npm-cli.js',node.parent.parent/'lib/node_modules/npm/bin/npm-cli.js']
        if shutil.which('npm'):
            candidates.append(Path(shutil.which('npm')).resolve())
        options.npm_cli = next((p for p in candidates if p.is_file() and p.name == 'npm-cli.js'),None)
    if options.npm_cli is None:
        raise Failure('specify existing npm-cli.js with --npm-cli')
    npm_cli = options.npm_cli.resolve()
    distribution = options.dist.resolve()
    manifest = json.loads((distribution/'npm-manifest.json').read_text())
    checks, skips, processes = [], [], []
    def check(value,label):
        if not value:
            raise Failure(label)
        checks.append(label)
    check(len(manifest['packages']) == 7, 'exactly one thin entry and six native platform packages')
    records, packed_files = {}, {}
    for record in manifest['packages']:
        target = record['target']
        archive = distribution/record['file']
        check(archive.stat().st_size == record['size'] and digest(archive.read_bytes()) == record['sha256'], target+' tarball size and checksum')
        files = package_files(archive)
        check(sorted(files) == record['files'], target+' exact file allowlist')
        package = json.loads(files['package.json'][0])
        check(package['version'] == manifest['version'] and package['name'] == record['name'], target+' package identity/version')
        check(not package.get('scripts') and not package.get('dependencies'),target+' has no install scripts or nonoptional dependencies')
        if target == 'entry':
            check(package['bin'] == {'ferry-dock':'bin/ferry-dock.cjs'} and len(package['optionalDependencies']) == 6
                  and set(package['optionalDependencies'].values()) == {manifest['version']}, 'entry pins all six optional packages to exactly its version')
            check(not any(name.startswith('native/') for name in files), 'thin entry contains no native executable')
        else:
            check(package['os'] == [target.split('-')[0]] and package['cpu'] == [target.split('-')[1]], target+' npm platform constraints')
            core = json.loads(files['core.json'][0])
            binary_name = 'native/ferry-dock.exe' if target.startswith('win32-') else 'native/ferry-dock'
            check(len(files[binary_name][0]) == core['binarySize'] and digest(files[binary_name][0]) == core['binarySha256'],target+' executable identity')
        for name,(data,mode) in files.items():
            check(not any(p.startswith('.') for p in PurePosixPath(name).parts), target+' no dotfiles: '+name)
            if not name.startswith('native/'):
                check(not re.search(rb'(?:npm_[A-Za-z0-9]{36}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|#owner=[A-Za-z0-9_-]{32,})',data), target+' no credential pattern: '+name)
        records[target],packed_files[target] = record,files
    sums = (distribution/'SHA256SUMS').read_text().splitlines()
    expected_sums = {p['file']:p['sha256'] for p in manifest['packages']}
    expected_sums['npm-manifest.json'] = digest((distribution/'npm-manifest.json').read_bytes())
    check(len(sums) == len(expected_sums) and {row.split('  ',1)[1]:row.split('  ',1)[0] for row in sums} == expected_sums,'checksums cover exactly seven packages and npm provenance manifest')
    check(manifest['entrySource']['commit'] == manifest['coreCommit'] and manifest['entrySource']['dirty'] is False,'entry and native code share the same clean source identity')
    with private_directory() as (private,cleanup):
        prefix = private/'中文 package with spaces'
        prefix.mkdir(mode=0o700)
        home,cache = private/'home',private/'cache'
        home.mkdir(mode=0o700);cache.mkdir(mode=0o700)
        configs = [private/'user.npmrc',private/'global.npmrc']
        for path in configs:
            path.touch(mode=0o600)
        environment = {'HOME':str(home),'USERPROFILE':str(home),'PATH':str(node.parent)+os.pathsep+os.defpath,
                       'TMPDIR':str(private),'TMP':str(private),'TEMP':str(private),'LANG':'en_US.UTF-8','TERM':'xterm-256color',
                       'NPM_CONFIG_USERCONFIG':str(configs[0]),'NPM_CONFIG_GLOBALCONFIG':str(configs[1]),
                       'NPM_CONFIG_CACHE':str(cache),'NPM_CONFIG_OFFLINE':'true','NPM_CONFIG_IGNORE_SCRIPTS':'true',
                       'NPM_CONFIG_AUDIT':'false','NPM_CONFIG_FUND':'false','NPM_CONFIG_UPDATE_NOTIFIER':'false',
                       'NPM_CONFIG_REGISTRY':'https://registry.npmjs.org/'}
        for key in ('SystemRoot','WINDIR','COMSPEC','PATHEXT','LOCALAPPDATA'):
            if key in os.environ:
                environment[key] = os.environ[key]
        def run(command,label,timeout=30,cwd=prefix,success=True):
            try:
                value = subprocess.run([str(p) for p in command],cwd=cwd,env=environment,capture_output=True,timeout=timeout)
            except subprocess.TimeoutExpired:
                raise Failure(label+': timed out') from None
            if success:
                check(value.returncode == 0,label)
            return value
        observed = json.loads(run([node,'-p','JSON.stringify({node:process.versions.node,os:process.platform,cpu:process.arch})'],'inspect existing Node runtime').stdout)
        target = observed['os']+'-'+observed['cpu']
        check(target in records and int(observed['node'].split('.')[0]) >= 22,'actual runtime is one supported Node22+ platform')
        npm = [node,npm_cli]
        npm_version = run(npm+['--version'],'inspect existing npm runtime').stdout.decode().strip()
        host,entry_record = records[target],records['entry']
        install = npm+['install','--offline','--ignore-scripts','--no-audit','--no-fund','--package-lock=false','--prefix',prefix,
                       distribution/host['file'],distribution/entry_record['file']]
        run(install,'offline local install with explicit native and entry tarballs; scripts disabled',timeout=90)
        installed = prefix/'node_modules'/entry_record['name']
        native_package = prefix/'node_modules'/host['name']
        entry = installed/'bin/ferry-dock.cjs'
        binary_name = 'ferry-dock.exe' if target.startswith('win32-') else 'ferry-dock'
        binary = native_package/'native'/binary_name
        check(entry.is_file() and binary.is_file(),'matching platform package installed beside thin entry')
        omitted = private/'omitted optional dependencies'
        run(npm+['install','--offline','--ignore-scripts','--omit=optional','--no-audit','--no-fund','--package-lock=false','--prefix',omitted,distribution/entry_record['file']],'entry can install offline with optional packages deliberately omitted')
        missing = run([node,omitted/'node_modules'/entry_record['name']/'bin/ferry-dock.cjs','version'],'omitted optional package runtime rejection',success=False)
        check(missing.returncode == 127 and not missing.stdout and b'optional' in missing.stderr,'--omit=optional produces actionable error without binary download')

        check(digest(binary.read_bytes()) == digest(packed_files[target]['native/'+binary_name][0]),'installed native executable equals tarball')
        def cli(*args,success=True,timeout=30):
            return run([node,entry,*args],'wrapper command exit zero',timeout=timeout,success=success)
        result = run(npm+['exec','--offline','--yes=false','--prefix',prefix,'--','ferry-dock','version'],'local npm exec stays offline')
        version = json.loads(result.stdout)
        check(version['version'] == manifest['version'] and version['commit'] == manifest['coreCommit'],'exact clean native version/commit through npm')
        invalid = cli('not-a-command',success=False)
        check(invalid.returncode == 2 and not invalid.stdout,'native stderr/exit2 preserved without stdout pollution')
        check(not cli('request','create','--help').stdout,'help does not pollute JSON stdout')
        # Repack root and selected platform: exact file bytes, never install scripts.
        repack = private/'repack';repack.mkdir()
        for package_dir,expected,target_label in ((installed,packed_files['entry'],'entry'),(native_package,packed_files[target],target)):
            info = json.loads(run(npm+['pack',package_dir,'--offline','--ignore-scripts','--json','--pack-destination',repack],target_label+' local repack').stdout)[0]
            actual = package_files(repack/info['filename'])
            check(set(actual) == set(expected) and all(actual[n][0] == expected[n][0] for n in expected),target_label+' repack preserves allowlist and bytes')
        # Clone only this run's node_modules for negative installation tests.
        for kind in ('missing-optional','wrong-version','tampered','missing-binary','unexecutable'):
            if kind == 'unexecutable' and os.name == 'nt':
                skips.append('POSIX executable mode rejection: not applicable on Windows')
                continue
            clone = private/('negative-'+kind)
            shutil.copytree(prefix/'node_modules',clone/'node_modules')
            p = clone/'node_modules'/host['name']
            b = p/'native'/binary_name
            if kind == 'missing-optional':
                shutil.rmtree(p)
            elif kind == 'wrong-version':
                meta = json.loads((p/'package.json').read_text());meta['version']='0.0.0';(p/'package.json').write_text(json.dumps(meta))
            elif kind == 'tampered':
                data = b.read_bytes(); b.write_bytes(bytes([data[0]^1])+data[1:])
            elif kind == 'missing-binary':
                b.unlink()
            else:
                b.chmod(0o600)
            bad = run([node,clone/'node_modules'/entry_record['name']/'bin/ferry-dock.cjs','version'],kind+' rejects',success=False)
            expected = 127 if kind in ('missing-optional','missing-binary') else 126 if kind == 'unexecutable' else 1
            check(bad.returncode == expected and not bad.stdout and bad.stderr,kind+' actionable failure without download/stdout')
        # Native process/HTTP acceptance with synthetic non-sensitive input only.
        state = None
        control = None
        shutdown_observation = {}
        opener = build_opener(ProxyHandler({}))
        def api(method,route,token,payload=None):
            body = json.dumps(payload).encode() if payload is not None else None
            request = Request(state['serverUrl']+route,data=body,method=method,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
            try:
                response = opener.open(request,timeout=5)
            except HTTPError as error:
                response=error
            with response:
                raw=response.read(); return response.status,json.loads(raw) if raw else None
        try:
            state_dir = private/'desktop 状态 with spaces'
            control = state_dir/'control.json'
            started = json.loads(cli('desktop','--no-open','--state-dir',state_dir,'--listen','127.0.0.1:0').stdout)
            check(started.get('state') == 'ready' and not started.get('reused'),'owned no-browser desktop starts and launcher returns')
            control = Path(started['controlPath']);state=json.loads(control.read_text())
            check(api('GET','/api/desktop',state['ownerToken'])[0] == 200,'Go service survives Node launcher completion')
            again=json.loads(cli('desktop','--no-open','--state-dir',state_dir,'--listen','127.0.0.1:0').stdout)
            check(again.get('reused') is True,'same-version authenticated desktop reused')
            handle=private/'中文 request handle with spaces.json'
            marker=private/'SHELL_MUST_NOT_RUN'
            prompt='中文 "quoted" ; $(touch '+str(marker)+') `touch '+str(marker)+'`'
            created=json.loads(cli('request','create','--control',control,'--task-id','npm-literal','--prompt',prompt,'--handle',handle,'--ttl','15m').stdout)
            check(created['request']['prompt']==prompt and not marker.exists(),'Unicode quotes and shell metacharacters remain literal argv')
            waited=json.loads(cli('request','wait','--handle',handle,'--timeout','100ms').stdout)
            check(waited['request']['state']=='pending' and waited['timedOut'] is True,'bounded wait times out without canceling request')
            if os.name != 'nt':
                for sig in (signal.SIGINT,signal.SIGTERM):
                    process=subprocess.Popen([str(node),str(entry),'request','wait','--handle',str(handle),'--timeout','10s'],cwd=prefix,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
                    processes.append(process);time.sleep(.3);process.send_signal(sig)
                    output,_=process.communicate(timeout=15)
                    check(process.returncode==130 and json.loads(output)['error']['code']=='wait_canceled',signal.Signals(sig).name+' forwarded to Go wait, exit130')
                    check(json.loads(cli('request','status','--handle',handle).stdout)['state']=='pending','signal interrupted wait only')
                # PTY console generated Ctrl+C on real POSIX host.
                import errno, fcntl, select, termios
                master,slave=os.openpty();attrs=termios.tcgetattr(slave);attrs[3]=(attrs[3]|termios.ISIG)&~termios.ECHO;termios.tcsetattr(slave,termios.TCSANOW,attrs)
                def terminal_child():
                    os.setsid();fcntl.ioctl(slave,termios.TIOCSCTTY,0)
                try:
                    process=subprocess.Popen([str(node),str(entry),'request','wait','--handle',str(handle),'--timeout','10s'],cwd=prefix,env=environment,stdin=slave,stdout=slave,stderr=slave,preexec_fn=terminal_child)
                    processes.append(process);os.close(slave);slave=None;time.sleep(.3);os.write(master,b'\x03');captured=b'';deadline=time.monotonic()+15
                    while time.monotonic()<deadline:
                        ready,_,_=select.select([master],[],[],.1)
                        if ready:
                            try: piece=os.read(master,65536)
                            except OSError as error:
                                if error.errno==errno.EIO:break
                                raise
                            if not piece:break
                            captured+=piece
                        elif process.poll() is not None:break
                    process.wait(timeout=2)
                    rows=[line for line in captured.splitlines() if line.startswith(b'{')]
                    check(process.returncode==130 and rows and json.loads(rows[-1])['error']['code']=='wait_canceled','real POSIX PTY Ctrl+C cancellation')
                finally:
                    if slave is not None:os.close(slave)
                    os.close(master)
            else:
                skips.append('Windows real console Ctrl+C/CTRL_BREAK: needs interactive console; bounded wait and explicit request cancel tested')
            fragment=parse_qs(urlsplit(created['sendUrl']).fragment)
            text='  npm phone → same task\n客户：增加两周试点。  '
            input_route='/api/requests/'+fragment['request'][0]+'/input'
            delivery={'idempotencyKey':'npm-input-one','text':text}
            delivered_code,delivered=api('POST',input_route,fragment['key'][0],delivery)
            check(delivered_code==201,'synthetic sender submission')
            duplicate_code,duplicate=api('POST',input_route,fragment['key'][0],delivery)
            check(duplicate_code==200 and duplicate['id']==delivered['id'],'duplicate sender retry returns the same receipt without another input')
            read=json.loads(cli('request','read','--handle',handle).stdout);repeat=json.loads(cli('request','read','--handle',handle).stdout)
            check(read['input']['text']==text and read['input']['trust']=='untrusted_user_input' and read['input']['id']==repeat['input']['id'],'request exact untrusted text and stable repeated read')
            canceled_handle=private/'cancel.json'
            cli('request','create','--control',control,'--task-id','npm-cancel','--prompt','cancel example','--handle',canceled_handle)
            canceled=json.loads(cli('request','cancel','--handle',canceled_handle).stdout)
            check(canceled['state']=='canceled','explicit request cancellation remains distinct')
            code,session=api('POST','/api/sessions',state['ownerToken'],{})
            check(code==201,'ordinary transfer still available')
            token=parse_qs(urlsplit(session['sendUrl']).fragment)['key'][0];route='/api/sessions/'+session['id']
            check(api('POST',route+'/messages',token,{'idempotencyKey':'npm-ordinary','text':text})[0]==201,'ordinary sender accepted')
            code,inbox=api('GET',route,state['ownerToken']);check(code==200 and inbox['messages'][0]['text']==text,'ordinary read exact text')
            check(api('POST','/api/desktop/quit',state['ownerToken'],{})[0]==202,'own desktop Quit accepted')
            stopped=wait_for_owned_stop(control,state['serverUrl'],opener,observations=shutdown_observation)
            check(not control.exists(),'owned control removed after Quit')
            check(stopped,'owned service socket refused connections after Quit: '+json.dumps(shutdown_observation,sort_keys=True))
            state=None
        finally:
            if state is None and control is not None and control.exists():
                try: state=json.loads(control.read_text())
                except Exception:
                    cleanup['preserve']=True
                    raise Failure('private control unreadable; cleanup uncertain and artifacts retained at '+str(private)) from None
            if state is not None:
                stopped=False
                for attempt in range(3):
                    try:api('POST','/api/desktop/quit',state['ownerToken'],{})
                    except Exception:pass
                    stopped=wait_for_owned_stop(control,state['serverUrl'],opener,timeout=5,observations=shutdown_observation)
                    if stopped:break
                if not stopped:
                    cleanup['preserve']=True
                    raise Failure('owned service cleanup uncertain; observation='+json.dumps(shutdown_observation,sort_keys=True)+'; private artifacts retained at '+str(private))
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=15)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=2)
        # Dispatch VM covers all targets without misrepresenting foreign native tests.
        vm=Path(__file__).resolve().parents[1]/'npm/test-dispatch.cjs'
        dispatch=json.loads(run([node,vm,entry],'six-platform VM dispatch, guards and spawn semantics').stdout)
        check(dispatch.get('scope')=='VM_ONLY' and dispatch.get('targets')==6,'VM dispatch explicitly separate from native acceptance')
    receipt={'status':'PASS_LOCAL','platform':target,'node':observed['node'],'npm':npm_version,'version':manifest['version'],
             'coreIdentity':version,'shutdownObservation':shutdown_observation,'checks':checks,'skipped':skips,'scope':'local seven tarballs, offline install/exec on current host; no registry publication',
             'notRun':['public registry/npx install','default browser opening','actual other OS/CPU in this run','browser download/Gatekeeper/SmartScreen first launch','real phone/LAN/QR','actual Codex host']}
    options.receipt.parent.mkdir(parents=True,exist_ok=True);options.receipt.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'PASS_LOCAL','checks':len(checks),'platform':target,'receipt':str(options.receipt),'skipped':skips,'shutdownObservation':shutdown_observation},ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (Failure,OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        print(json.dumps({'status':'FAIL','reason':str(error) if isinstance(error,Failure) else type(error).__name__}));raise SystemExit(1)
