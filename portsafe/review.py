"""Session-local review notes. Never changes or authorizes allocations."""
import hashlib
import json
from datetime import datetime, timezone


def snapshot_id(report):
    return hashlib.sha256(json.dumps(report, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode('utf-8')).hexdigest()


def record_review(report, history, task_id, status, reason):
    rows = {r['task']: r for r in report['plan']['assignments']}
    if task_id not in rows:
        raise ValueError('현재 계획에 없는 작업입니다.')
    if status not in ('검토 확인', '보류', '입력 정정 요청'):
        raise ValueError('허용되지 않은 검토 상태입니다.')
    if status == '검토 확인' and rows[task_id]['worker'] is None:
        raise ValueError('미배정 작업은 검토 확인으로 처리할 수 없습니다. 보류 또는 입력 정정 요청을 사용하세요.')
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValueError('검토 사유를 1~500자로 입력하세요.')
    identity = snapshot_id(report)
    if any(r['snapshot_id'] != identity for r in history):
        raise ValueError('다른 입력 또는 계획의 검토 이력을 혼합할 수 없습니다.')
    return [*history, dict(sequence=len(history)+1, snapshot_id=identity,
        timestamp_utc=datetime.now(timezone.utc).isoformat(), task_id=task_id,
        assigned_worker=rows[task_id]['worker'], status=status, reason=reason.strip(),
        data_origin='SIMULATED', execution_authorized=False)]
