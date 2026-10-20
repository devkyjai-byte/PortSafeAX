from zipfile import ZipFile

import pytest

from scripts.package_demo import build, verify, write_receipt, SOURCES


def test_package_reproducibility_and_allowlist(tmp_path):
    first = build(tmp_path / 'first.zip')
    second = build(tmp_path / 'second.zip')
    assert first.read_bytes() == second.read_bytes()
    manifest = verify(first)
    assert set(manifest['files']) == set(SOURCES) | {'START_HERE.txt'}
    with ZipFile(first) as archive:
        assert b'PortSafeAX_allocation_demo.html' in archive.read('index.html')
        assert b'index.html' in archive.read('PortSafeAX_allocation_demo.html')


@pytest.mark.parametrize('change', ['tamper', 'missing', 'extra'])
def test_reject_changed_package(tmp_path, change):
    original = build(tmp_path / 'original.zip')
    broken = tmp_path / 'broken.zip'
    with ZipFile(original) as source, ZipFile(broken, 'w') as target:
        for name in source.namelist():
            if change == 'missing' and name == 'index.html':
                continue
            data = source.read(name)
            if change == 'tamper' and name == 'index.html':
                data += b'changed'
            target.writestr(name, data)
        if change == 'extra':
            target.writestr('private.txt', 'must not be shipped')
    with pytest.raises(ValueError):
        verify(broken)


def test_receipt_binds_package_hash_and_metadata(tmp_path):
    package = build(tmp_path / 'demo.zip')
    receipt_path = tmp_path / 'build_receipt.json'
    receipt = write_receipt(package, receipt_path, 'abc123', 'https://example.test/run/1')
    assert receipt['commit'] == 'abc123'
    assert receipt['run_url'].endswith('/run/1')
    assert receipt['sha256']
    assert receipt == __import__('json').loads(receipt_path.read_text(encoding='utf-8'))
