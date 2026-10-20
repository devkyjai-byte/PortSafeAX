"""Synthetic relative-motion demonstration, not a device safety controller."""
from dataclasses import asdict, dataclass
import math

VERSION = 'proximity-demo-0.1'


@dataclass(frozen=True)
class Sample:
    x: float  # metres, right positive
    y: float  # metres, forward positive
    vx: float  # relative m/s; provided synthetic ground truth, NOT radar output
    vy: float
    health: str = 'ok'
    age: float = 0.0


CASES = {
    'front': ('전방 접근', Sample(0, 10, 0, -2)),
    'rear': ('후방 접근', Sample(0, -6, 0, 2)),
    'crossing': ('측면 교차', Sample(6, 0, -2, 0)),
    'passing': ('옆으로 통과', Sample(5, 10, 0, -2)),
    'receding': ('멀어지는 차량', Sample(0, 5, 0, 2)),
    'near_static': ('가까운 정지 물체', Sample(0, 1, 0, 0)),
    'blocked': ('센서 가림', Sample(0, 10, 0, -2, health='blocked')),
    'stale': ('오래된 관측', Sample(0, 10, 0, -2, age=2)),
}


def evaluate(sample):
    config = {'horizon_s': 6.0, 'clearance_m': 2.0, 'max_age_s': 0.5}
    result = {
        'data_origin': 'SIMULATED', 'model_type': 'UNVALIDATED_RULES',
        'version': VERSION, 'config': config, 'input': asdict(sample),
        'status': 'UNKNOWN', 'label': '판단 불가 / 감지 제한',
        'reason': '', 'direction': None, 'distance_m': None,
        'closest_time_s': None, 'closest_distance_m': None,
        'alert_entry_s': None,
        'limits': '합성 상대 위치·속도를 정답으로 입력한 점 표적 계산입니다. 센서 검출·AI·차량 제동·현장 안전 검증이 아닙니다.',
    }
    values = (sample.x, sample.y, sample.vx, sample.vy, sample.age)
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values) or sample.age < 0:
        result['reason'] = '비정상 입력: 경고 없음으로 취급하지 않습니다.'
        return result
    if sample.health != 'ok' or sample.age > config['max_age_s']:
        result['reason'] = '센서 상태 이상 또는 관측 유효시간 초과. 위치·경로를 판정하지 않습니다.'
        return result
    x, y, vx, vy = sample.x, sample.y, sample.vx, sample.vy
    radius, horizon = config['clearance_m'], config['horizon_s']
    distance = math.hypot(x, y)
    direction = ('전방' if y >= 0 else '후방') if abs(y) >= abs(x) else ('우측' if x >= 0 else '좌측')
    speed2, dot = vx * vx + vy * vy, x * vx + y * vy
    t = min(horizon, max(0.0, -dot / speed2)) if speed2 > 0 else 0.0
    closest = math.hypot(x + vx * t, y + vy * t)
    # First entry into an illustrative circular zone, not time to physical collision.
    entry = None
    if distance <= radius:
        entry = 0.0
    elif speed2 > 0:
        disc = dot * dot - speed2 * (distance * distance - radius * radius)
        if disc >= 0:
            candidate = (-dot - math.sqrt(disc)) / speed2
            if 0 <= candidate <= horizon:
                entry = candidate
    result.update(direction=direction, distance_m=distance,
                  closest_time_s=t, closest_distance_m=closest, alert_entry_s=entry)
    if entry is not None:
        result.update(status='ALERT', label='주의 / 합성 경고 조건 충족',
                      reason='시연 경계 안에 있거나, 일정 상대속도 가정에서 관측 구간 내 경계 진입이 예상됩니다.')
    else:
        result.update(status='NO_ALERT', label='이 시연 규칙의 경고 조건 미충족',
                      reason='계산 구간 내 시연 경계 진입이 없습니다. 안전 확인이나 다른 방향의 무위험을 뜻하지 않습니다.')
    return result


def reports():
    return {key: {'title': title, **evaluate(sample)} for key, (title, sample) in CASES.items()}
