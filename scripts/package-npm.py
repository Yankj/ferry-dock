#!/usr/bin/env python3
"""Pack a thin npm entry and six exact-version native platform packages locally.

Reads a clean native CLI distribution manifest. Uses only local files and an
existing Node/npm CLI; no registry requests, install hooks or publication.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {'darwin-arm64': ('darwin','arm64'), 'darwin-x64': ('darwin','amd64'),
           'linux-arm64': ('linux','arm64'), 'linux-x64': ('linux','amd64'),
           'win32-arm64': ('windows','arm64'), 'win32-x64': ('windows','amd64')}
COPY_FILES = {'npm/bin/ferry-dock.cjs':'bin/ferry-dock.cjs', 'npm/README.md':'README.md',
              'LICENSE':'LICENSE', 'THIRD_PARTY_NOTICES.md':'THIRD_PARTY_NOTICES.md',
              'skills/ferry-dock/SKILL.md':'skills/ferry-dock/SKILL.md',
              'docs/contracts/request-v1.md':'docs/contracts/request-v1.md'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def require(value, message):
    if not value:
        raise ValueError(message)

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def binary_bytes(path, artifact):
    data = path.read_bytes()
    require(len(data) == artifact['size'] and sha(data) == artifact['sha256'], 'native archive size/checksum mismatch')
    expected = artifact['binary']
    require(0 < expected['size'] <= 32 << 20, 'invalid native executable size')
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            require(len(members) == len({m.filename for m in members}), 'duplicate native archive member')
            chosen = archive.getinfo(expected['path'])
            require(not chosen.is_dir() and chosen.file_size == expected['size'], 'invalid native executable member')
            value = archive.read(chosen)
    else:
        with tarfile.open(path, 'r:gz') as archive:
            members = archive.getmembers()
            require(len(members) == len({m.name for m in members}), 'duplicate native archive member')
            chosen = archive.getmember(expected['path'])
            require(chosen.isfile() and chosen.size == expected['size'], 'invalid native executable member')
            value = archive.extractfile(chosen).read()
    for member in members:
        name = member.filename if hasattr(member, 'filename') else member.name
        parts = PurePosixPath(name).parts
        require(not name.startswith('/') and '\\' not in name and '..' not in parts, 'unsafe native archive member')
    require(len(value) == expected['size'] and sha(value) == expected['sha256'], 'native executable checksum mismatch')
    return value

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, required=True, help='native distribution directory with all six CLI artifacts and manifest.json')
    parser.add_argument('--out', type=Path, default=ROOT/'dist/npm', help='output parent; new version directory only')
    parser.add_argument('--package-name', default='ferry-dock', help='candidate name, not registry ownership')
    parser.add_argument('--node', default=shutil.which('node'), help='existing Node executable (default PATH)')
    parser.add_argument('--npm-cli', type=Path, help='existing npm-cli.js; automatically located beside Node/npm when omitted')
    args = parser.parse_args()
    require(args.node, 'existing Node executable was not found')
    args.node = str(Path(args.node).resolve())
    if args.npm_cli is None:
        base = Path(args.node).parent
        candidates = [base/'node_modules/npm/bin/npm-cli.js', base.parent/'lib/node_modules/npm/bin/npm-cli.js']
        located = shutil.which('npm')
        if located:
            candidates.append(Path(located).resolve())
        args.npm_cli = next((p for p in candidates if p.is_file() and p.name == 'npm-cli.js'), None)
    require(args.npm_cli and args.npm_cli.is_file(), 'npm-cli.js not found; specify --npm-cli')
    require(re.fullmatch(r'(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*', args.package_name), 'invalid candidate package name')
    source = args.dist.resolve()
    manifest_data = (source/'manifest.json').read_bytes()
    manifest = json.loads(manifest_data)
    version = manifest['version']
    require(re.fullmatch(r'\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', version), 'invalid version')
    require(manifest['schema'] == 1 and manifest['source']['dirty'] is False, 'requires clean native source manifest')
    head = subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    status = subprocess.run(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT,capture_output=True,text=True,check=True).stdout
    require(not status and head == manifest['source']['commit'], 'npm source must be clean and match the native source commit')
    snapshots = {name:(ROOT/name).read_bytes() for name in [*COPY_FILES,'npm/package.json']}

    require(re.fullmatch(r'[a-f0-9]{40}', manifest['source']['commit']), 'invalid source commit')
    template = json.loads((ROOT/'npm/package.json').read_text())
    require(template['version'] == version, 'npm source version must equal native distribution version')
    destination = args.out.resolve()/version
    require(not destination.exists(), 'output version directory exists; use a new --out parent')
    natives, platforms = {}, {}
    for target, (goos, goarch) in TARGETS.items():
        found = [a for a in manifest['artifacts'] if a['kind'] == 'cli' and a['goos'] == goos and a['goarch'] == goarch]
        require(len(found) == 1, 'manifest must contain one CLI per supported platform: '+target)
        artifact = found[0]
        require(Path(artifact['file']).name == artifact['file'], 'invalid archive filename')
        native = binary_bytes(source/artifact['file'], artifact)
        name = args.package_name+'-'+target
        platforms[target] = {'packageName':name, 'binarySize':len(native), 'binarySha256':sha(native),
                             'archiveName':artifact['file'], 'archiveSha256':artifact['sha256']}
        natives[target] = native
    core = {'schemaVersion':2, 'version':version, 'commit':manifest['source']['commit'],
            'manifestSha256':sha(manifest_data), 'platforms':platforms}
    destination.mkdir(parents=True)
    stages = destination/'stages'
    stages.mkdir()
    entry = stages/'entry'
    entry.mkdir()
    for original_name, target_name in COPY_FILES.items():
        original = ROOT/original_name
        require(original.is_file() and not original.is_symlink(), 'packaging input must be regular')
        target = entry/target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original,target)
        target.chmod(0o755 if target_name == 'bin/ferry-dock.cjs' else 0o644)
    template['name'] = args.package_name
    template['optionalDependencies'] = {platforms[t]['packageName']:version for t in TARGETS}
    write_json(entry/'package.json',template)
    write_json(entry/'core.json',core)
    jobs = [('entry',entry, sorted([*COPY_FILES.values(),'package.json','core.json']))]
    for target, values in platforms.items():
        stage = stages/target
        stage.mkdir()
        package = {k:template[k] for k in ('description','license','repository','homepage','bugs','publishConfig')}
        package.update({'name':values['packageName'], 'version':version, 'os':[target.split('-')[0]],
                        'cpu':[target.split('-')[1]], 'files':['native/','core.json','README.md','LICENSE','THIRD_PARTY_NOTICES.md']})
        native_name = 'native/ferry-dock.exe' if target.startswith('win32-') else 'native/ferry-dock'
        write_json(stage/'package.json', package)
        write_json(stage/'core.json', {k:v for k,v in core.items() if k != 'platforms'} | {'target':target, **values})
        for filename in ('README.md','LICENSE','THIRD_PARTY_NOTICES.md'):
            shutil.copyfile(entry/filename,stage/filename)
        output = stage/native_name
        output.parent.mkdir()
        output.write_bytes(natives[target])
        output.chmod(0o755)
        jobs.append((target,stage,sorted(['package.json','core.json','README.md','LICENSE','THIRD_PARTY_NOTICES.md',native_name])))
    results = []
    with tempfile.TemporaryDirectory(prefix='ferry-dock-npm-pack-') as private:
        user_config, global_config = Path(private)/'user.npmrc', Path(private)/'global.npmrc'
        user_config.touch(); global_config.touch()
        environment = dict(os.environ, npm_config_update_notifier='false', npm_config_audit='false', npm_config_fund='false',
                           npm_config_userconfig=str(user_config),npm_config_globalconfig=str(global_config))
        for target, stage, expected_files in jobs:
            command = [str(Path(args.node).resolve()),str(args.npm_cli.resolve()),'pack','--ignore-scripts','--json','--pack-destination',str(destination),
                       '--cache',private,'--userconfig',str(user_config),'--globalconfig',str(global_config),'--offline','--logs-max=0','--loglevel=error']
            result = subprocess.run(command,cwd=stage,env=environment,capture_output=True,text=True,timeout=60)
            require(result.returncode == 0, 'local npm pack failed; no publication attempted')
            packed = json.loads(result.stdout)
            require(len(packed) == 1, 'expected one package')
            packed = packed[0]
            require(sorted(f['path'] for f in packed['files']) == expected_files, 'npm package violates content allowlist')
            tarball = destination/packed['filename']
            with tarfile.open(tarball) as archive:
                for member in archive:
                    require(member.isfile() and member.name.startswith('package/') and member.name[8:] in expected_files,'unexpected npm member')
            results.append({'target':target,'name':json.loads((stage/'package.json').read_text())['name'], 'version':version,
                            'file':tarball.name,'size':tarball.stat().st_size,'sha256':sha(tarball.read_bytes()),'files':expected_files})
    require(all((ROOT/name).read_bytes() == data for name,data in snapshots.items()), 'npm source changed during packaging')
    final_head = subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    final_status = subprocess.run(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT,capture_output=True,text=True,check=True).stdout
    require(final_head == head and not final_status, 'source identity changed during packaging')
    shutil.rmtree(stages)
    receipt = {'schemaVersion':1,'status':'LOCAL_UNPUBLISHED','version':version,'coreCommit':core['commit'],
               'entrySource':{'commit':head,'dirty':False},
               'nativeManifestSha256':core['manifestSha256'],'packages':results}
    write_json(destination/'npm-manifest.json',receipt)
    (destination/'SHA256SUMS').write_text(''.join(f"{p['sha256']}  {p['file']}\n" for p in results)+sha((destination/'npm-manifest.json').read_bytes())+'  npm-manifest.json\n', encoding='utf-8')
    print(json.dumps({'status':'LOCAL_UNPUBLISHED','directory':str(destination),'packages':len(results),'version':version}))

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, tarfile.TarError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        raise SystemExit('Ferry Dock npm packaging failed: '+str(error))
