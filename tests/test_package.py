from zipfile import ZipFile

import pytest

from scripts.package_demo import build, verify, SOURCES


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
