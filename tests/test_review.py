from copy import deepcopy
import pytest
from portsafe.review import record_review, snapshot_id


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
