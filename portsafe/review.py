"""Session-local review notes. Never changes or authorizes allocations."""
import hashlib
import json
from datetime import datetime, timezone

MAX_REVIEW_BYTES = 2 * 1024 * 1024
MAX_REVIEW_EVENTS = 1000


def snapshot_id(report):
    return hashlib.sha256(json.dumps(report, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode('utf-8')).hexdigest()


def record_review(report, history, task_id, status, reason):
    if len(history) >= MAX_REVIEW_EVENTS:
        raise ValueError('한 계획의 검토 기록은 최대 1,000건입니다.')
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


def export_reviews(report, history):
    return json.dumps(dict(snapshot_id=snapshot_id(report), plan_snapshot=report,
                           review_history=history,
                           disclaimer='세션 내 합성 검토 메모. 인증된 승인 또는 현장 실행 기록이 아님.'),
                      ensure_ascii=False, indent=2, allow_nan=False)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('JSON에 중복된 항목 이름이 있습니다.')
        result[key] = value
    return result


def restore_reviews(report, current_history, raw):
    """Validate a downloaded memo and extend only a matching existing prefix.

    Hashes bind the memo to the current plan, not to an authenticated author.
    This never imports an allocation or replaces conflicting local history.
    """
    if not isinstance(raw, bytes) or len(raw) > MAX_REVIEW_BYTES:
        raise ValueError('2MB 이하의 JSON 파일을 선택하세요.')
    try:
        document = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique_object)
        identity = snapshot_id(report)
        if (not isinstance(document, dict)
                or document.get('snapshot_id') != identity
                or snapshot_id(document.get('plan_snapshot')) != identity):
            raise ValueError('현재 입력·계획과 파일이 다릅니다. 저장 당시 시나리오·시드를 선택하세요.')
        events = document.get('review_history')
        if not isinstance(events, list) or not 1 <= len(events) <= MAX_REVIEW_EVENTS:
            raise ValueError('검토 기록은 1~1,000건이어야 합니다.')
        fields = {'sequence', 'snapshot_id', 'timestamp_utc', 'task_id',
                  'assigned_worker', 'status', 'reason', 'data_origin', 'execution_authorized'}
        for number, event in enumerate(events, 1):
            if not isinstance(event, dict) or set(event) != fields:
                raise ValueError('검토 기록의 항목 구성이 올바르지 않습니다.')
            if (type(event['sequence']) is not int or event['sequence'] != number
                    or event['snapshot_id'] != identity
                    or event['execution_authorized'] is not False
                    or event['data_origin'] != 'SIMULATED'):
                raise ValueError('검토 순서·계획 식별자·합성 데이터 표시가 올바르지 않습니다.')
            try:
                stamp = datetime.fromisoformat(event['timestamp_utc'])
            except (TypeError, ValueError) as exc:
                raise ValueError('기록 시각 형식이 올바르지 않습니다.') from exc
            if stamp.utcoffset() != timezone.utc.utcoffset(stamp):
                raise ValueError('기록 시각에 UTC 시간대가 필요합니다.')
            # Reuse the same eligibility rules as newly entered memos.
            checked = record_review(report, [], event['task_id'], event['status'], event['reason'])[0]
            if event['assigned_worker'] != checked['assigned_worker']:
                raise ValueError('기록의 배정 작업자가 현재 계획과 다릅니다.')
        if len(events) < len(current_history) or events[:len(current_history)] != current_history:
            raise ValueError('현재 검토 이력과 충돌합니다. 기존 기록을 덮어쓰지 않습니다.')
        return events
    except (KeyError, TypeError, UnicodeError, RecursionError, OverflowError) as exc:
        raise ValueError('검토 JSON의 형식 또는 문자 인코딩이 올바르지 않습니다.') from exc
    except json.JSONDecodeError as exc:
        raise ValueError('올바른 JSON 파일이 아닙니다.') from exc
