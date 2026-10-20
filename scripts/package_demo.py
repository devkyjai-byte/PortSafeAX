"""Build and verify an allowlisted offline demo, without proposal/source documents."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'index.html': 'demo/index.html',
    'PortSafeAX_allocation_demo.html': 'demo/PortSafeAX_allocation_demo.html',
    'PortSafeAX_allocation_demo.json': 'demo/PortSafeAX_allocation_demo.json',
    'PortSafeAX_proximity_demo.html': 'demo/PortSafeAX_proximity_demo.html',
    'PortSafeAX_proximity_demo.json': 'demo/PortSafeAX_proximity_demo.json',
    '열람안내.md': 'demo/열람안내.md',
    'verification_metrics.json': 'data/verification_metrics.json',
}
START = '''PortSafe AX — 오프라인 합성 시연

1. ZIP 안에서 바로 실행하지 말고 전체 압축을 푸세요.
2. index.html을 브라우저로 여세요. 파일을 같은 폴더에 유지하세요.
3. 작업배정 또는 접근 경고 시연을 선택하세요.
4. 실제 사용할 PC에서 상황 선택·사유 펼치기·JSON 다운로드를 확인하세요.

모든 데이터는 합성입니다. 미검증 규칙이며 학습된 AI·실제 센서 연결은 없습니다.
경고 조건 미충족은 안전 확인이 아닙니다. SafeBack은 후속 확장입니다.
이 패키지는 사전 계산한 결과 탐색용입니다. 관리자 검토 기록과 실시간 재계산은
별도 로컬 앱에서만 제공하며 Python 앱·기획서·공모전 원본은 포함하지 않습니다.
열람안내의 run_demo.bat 언급은 전체 개발 저장소에 해당합니다.
이 ZIP은 시연 보조자료입니다. 필수 제출서류 묶음 또는 접수 완료 증빙이 아닙니다.

manifest.json은 파일 크기와 SHA-256을 기록합니다. 손상·차이 확인용이며
전자서명이나 제작자 인증이 아닙니다. 모든 파일의 실제 브라우저 검수는 별도입니다.
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build(destination, root=ROOT):
    # Normalize text line endings so Windows and Linux produce identical content.
    payload = {name: (root / source).read_text(encoding='utf-8').encode('utf-8')
               for name, source in SOURCES.items()}
    payload['START_HERE.txt'] = START.encode('utf-8')
    manifest = {
        'schema': 'portsafe-offline-demo-v1', 'data_origin': 'SIMULATED',
        'model_type': 'UNVALIDATED_RULES', 'entrypoint': 'index.html',
        'files': {name: {'bytes': len(data), 'sha256': digest(data)}
                  for name, data in sorted(payload.items())},
    }
    payload['manifest.json'] = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, 'w') as archive:
        for name, data in sorted(payload.items()):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    verify(destination)
    return destination


def verify(path):
    expected = set(SOURCES) | {'START_HERE.txt', 'manifest.json'}
    with ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(expected) or set(names) != expected:
            raise ValueError('Unexpected, duplicate, or missing package files')
        manifest = json.loads(archive.read('manifest.json'))
        if (manifest.get('schema') != 'portsafe-offline-demo-v1'
                or manifest.get('entrypoint') != 'index.html'
                or manifest.get('data_origin') != 'SIMULATED'
                or manifest.get('model_type') != 'UNVALIDATED_RULES'):
            raise ValueError('Invalid package metadata')
        if set(manifest['files']) != expected - {'manifest.json'}:
            raise ValueError('Manifest file list mismatch')
        for name, record in manifest['files'].items():
            data = archive.read(name)
            if len(data) != record['bytes'] or digest(data) != record['sha256']:
                raise ValueError(f'Content mismatch: {name}')
    return manifest


def write_receipt(package, destination, commit=None, run_url=None):
    package = Path(package)
    receipt = dict(
        commit=commit or os.environ.get('GITHUB_SHA', 'LOCAL'),
        run_url=run_url or os.environ.get('GITHUB_SERVER_URL', ''),
        package=package.name,
        sha256=digest(package.read_bytes()),
        data_origin='SIMULATED',
        model_type='UNVALIDATED_RULES',
        note='Automated software checks do not include browser or field validation. Not a digital signature.',
    )
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--receipt', type=Path, help='Write a provenance receipt for the generated package')
    parser.add_argument('--commit', help='Commit SHA to include in the receipt')
    parser.add_argument('--run-url', help='Verification run URL to include in the receipt')
    args = parser.parse_args()
    if args.verify:
        verify(args.verify)
        print('Package integrity OK')
    else:
        result = build(ROOT / 'deliverables/PortSafeAX_offline_demo.zip')
        print(f'Built {result.name}; SHA-256: {digest(result.read_bytes())}')
        if args.receipt:
            write_receipt(result, args.receipt, args.commit, args.run_url)
            print(f'Wrote {args.receipt}')
