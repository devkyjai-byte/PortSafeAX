from copy import deepcopy
import pytest
from portsafe.review import record_review, snapshot_id
from portsafe.review import export_reviews, restore_reviews, MAX_REVIEW_BYTES
import json


def report():
    return {'plan': {'assignments': [{'task':'T1','worker':'W1'}, {'task':'T2','worker':None}]}, 'seed':42}


def test_review_append_and_no_allocation_change():
    original=report(); saved=deepcopy(original)
    one=record_review(original, [], 'T1', '검토 확인', '조건 검토')
    two=record_review(original, one, 'T1', '보류', '추가 확인 필요')
    assert original==saved and len(one)==1 and len(two)==2
    assert [r['sequence'] for r in two]==[1,2]
    assert all(r['execution_authorized'] is False for r in two)


@pytest.mark.parametrize('task,status,reason',[('T2','검토 확인','확인'),('T9','보류','확인'),('T1','승인','확인'),('T1','보류','  '),('T1','보류','x'*501)])
def test_invalid_review_rejected(task,status,reason):
    with pytest.raises(ValueError): record_review(report(),[],task,status,reason)


def test_snapshot_isolation_and_unassigned_hold():
    a=report(); history=record_review(a,[],'T2','보류','자격 인력 확보 검토')
    b=deepcopy(a);b['seed']=43
    assert snapshot_id(a)!=snapshot_id(b)
    with pytest.raises(ValueError): record_review(b,history,'T1','보류','다른 사례')


def test_restore_roundtrip_extend_and_duplicate_without_mutation():
    plan = report(); original = deepcopy(plan)
    one = record_review(plan, [], 'T1', '검토 확인', '조건 확인')
    two = record_review(plan, one, 'T2', '보류', '자격 인력 확보 필요')
    raw = export_reviews(plan, two).encode('utf-8')
    assert restore_reviews(plan, [], raw) == two
    assert restore_reviews(plan, one, raw) == two
    assert restore_reviews(plan, two, raw) == two
    assert plan == original and len(one) == 1
    with pytest.raises(ValueError, match='충돌'):
        restore_reviews(plan, two, export_reviews(plan, one).encode('utf-8'))


@pytest.mark.parametrize('field,value', [
    ('sequence', True), ('sequence', 2), ('snapshot_id', 'other'),
    ('execution_authorized', True), ('execution_authorized', 0),
    ('data_origin', 'REAL'), ('assigned_worker', 'W9'),
    ('task_id', 'T2'), ('status', '승인'), ('reason', ' '),
    ('timestamp_utc', 'not a time'), ('timestamp_utc', '2026-10-20T12:00:00'),
])
def test_restore_rejects_invalid_events(field, value):
    plan = report(); history = record_review(plan, [], 'T1', '검토 확인', '확인')
    document = json.loads(export_reviews(plan, history))
    document['review_history'][0][field] = value
    with pytest.raises(ValueError):
        restore_reviews(plan, [], json.dumps(document).encode())


def test_restore_rejects_other_plan_and_conflicting_history():
    plan = report(); history = record_review(plan, [], 'T1', '보류', '확인')
    raw = export_reviews(plan, history).encode()
    other = deepcopy(plan); other['seed'] = 43
    with pytest.raises(ValueError, match='입력·계획'):
        restore_reviews(other, [], raw)
    conflicting = record_review(plan, [], 'T1', '보류', '다른 사유')
    with pytest.raises(ValueError, match='충돌'):
        restore_reviews(plan, conflicting, raw)
    forged = json.loads(raw); forged['plan_snapshot']['seed'] = 99
    with pytest.raises(ValueError, match='입력·계획'):
        restore_reviews(plan, [], json.dumps(forged).encode())


@pytest.mark.parametrize('raw', [b'not json', b'\xff', b'[]', b'{"x":1,"x":2}', b' ' * (MAX_REVIEW_BYTES + 1)],
                         ids=['invalid-json', 'invalid-utf8', 'wrong-root', 'duplicate-key', 'oversize'])
def test_restore_rejects_invalid_file(raw):
    with pytest.raises(ValueError):
        restore_reviews(report(), [], raw)
