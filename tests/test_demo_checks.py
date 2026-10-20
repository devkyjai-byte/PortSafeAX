from pathlib import Path

import pytest

from scripts.check_demo import check, check_file


def test_static_demo_bundle_is_self_contained():
    assert check()


def test_external_link_is_rejected(tmp_path):
    page = tmp_path / 'page.html'
    page.write_text('<a href="https://example.com">외부</a><p>합성 데이터 미검증 규칙</p>', encoding='utf-8')
    with pytest.raises(ValueError, match='external'):
        check_file(page)


def test_missing_local_link_is_rejected(tmp_path):
    page = tmp_path / 'page.html'
    page.write_text('<a href="missing.html">누락</a><p>합성 데이터 미검증 규칙</p>', encoding='utf-8')
    with pytest.raises(ValueError, match='missing'):
        check_file(page)
