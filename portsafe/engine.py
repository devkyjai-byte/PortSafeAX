"""Explainable rules; not a medical model or a validated ML predictor."""
from dataclasses import dataclass
import math


def number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name}: {low}~{high} 범위의 유한한 수가 필요합니다")


@dataclass(frozen=True)
class Worker:
    id: str
    qualifications: tuple[str, ...]
    hours: float
    fatigue: float
    load: float
    max_hours: float = 8
    max_fatigue: float = 80
    max_load: float = 300

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("작업자 ID가 필요합니다")
        if not isinstance(self.qualifications, tuple) or any(not isinstance(q, str) or not q.strip() for q in self.qualifications):
            raise ValueError("자격은 문자열 튜플이어야 합니다")
        for key in ('hours', 'load', 'max_hours', 'max_load'):
            number(getattr(self, key), key, 0, 10000)
        for key in ('fatigue', 'max_fatigue'):
            number(getattr(self, key), key, 0, 100)


@dataclass(frozen=True)
class Task:
    id: str
    qualification: str
    duration: float
    weight: float
    repetition: float
    posture: float
    heat: float
    priority: int = 1

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip() or not isinstance(self.qualification, str) or not self.qualification.strip():
            raise ValueError("작업 ID와 필요 자격이 필요합니다")
        number(self.duration, 'duration', 0.01, 24)
        for key in ('weight', 'repetition', 'posture', 'heat'):
            number(getattr(self, key), key, 0, 100)
        if type(self.priority) is not int or not 1 <= self.priority <= 3:
            raise ValueError("우선순위는 1~3 정수입니다")


def score(task):
    """All inputs normalized 0..100; illustrative weights, no empirical validity."""
    return round(.35 * task.weight + .25 * task.repetition + .25 * task.posture + .15 * task.heat, 2)


def increment(task):
    load = score(task) * task.duration
    return {'hours': task.duration, 'load': load, 'fatigue': load * .12}


def validate(workers, tasks):
    for items, label in ((workers, '작업자'), (tasks, '작업')):
        ids = [x.id for x in items]
        if len(ids) != len(set(ids)):
            raise ValueError(f"중복 {label} ID")


def initial(workers):
    return {w.id: dict(hours=w.hours, fatigue=w.fatigue, load=w.load) for w in workers}


def violations(worker, state, task):
    delta = increment(task)
    reasons = []
    if task.qualification not in worker.qualifications:
        reasons.append('자격 불충족')
    for key, label in (('hours', '근무시간'), ('fatigue', '피로'), ('load', '최대부하')):
        if state[key] + delta[key] > getattr(worker, 'max_' + key) + 1e-9:
            reasons.append(label + ' 상한 초과')
    return reasons


def apply(state, task):
    for key, value in increment(task).items():
        state[key] += value


def allocate(workers, tasks):
    """Deterministic greedy sequential allocation, not globally optimal scheduling."""
    validate(workers, tasks)
    state = initial(workers)
    rows = []
    for task in sorted(tasks, key=lambda t: (-t.priority, -score(t), t.id)):
        rejected = {w.id: violations(w, state[w.id], task) for w in workers}
        feasible = [w for w in workers if not rejected[w.id]]
        if feasible:
            def cost(w):
                d = increment(task)
                return (max((state[w.id][k] + d[k]) / max(getattr(w, 'max_' + k), 1e-9) for k in d), w.id)
            chosen = min(feasible, key=cost)
            apply(state[chosen.id], task)
            rows.append(dict(task=task.id, worker=chosen.id, reason='모든 제약 충족', rejected=rejected))
        else:
            rows.append(dict(task=task.id, worker=None, reason='가능한 작업자 없음' if workers else '작업자 없음', rejected=rejected))
    return dict(assignments=rows, states=state)


def allocate_reference(workers, tasks):
    """Same task ordering and constraints; choose first eligible worker by ID.

    A reproducible simple comparator, not a representation of field practice.
    """
    validate(workers, tasks)
    state = initial(workers)
    rows = []
    for task in sorted(tasks, key=lambda t: (-t.priority, -score(t), t.id)):
        rejected = {w.id: violations(w, state[w.id], task) for w in workers}
        feasible = sorted((w for w in workers if not rejected[w.id]), key=lambda w: w.id)
        chosen = feasible[0] if feasible else None
        if chosen:
            apply(state[chosen.id], task)
        rows.append(dict(task=task.id, worker=chosen.id if chosen else None,
                         reason='ID순 첫 제약 충족 후보' if chosen else '가능한 작업자 없음',
                         rejected=rejected))
    return dict(assignments=rows, states=state)


def audit(workers, tasks, mapping):
    """Evaluate baseline in supplied task order, including unsafe assignments."""
    validate(workers, tasks)
    by_worker = {w.id: w for w in workers}
    if set(mapping) - {t.id for t in tasks}:
        raise ValueError('알 수 없는 작업 ID')
    state = initial(workers)
    rows = []
    for task in tasks:
        wid = mapping.get(task.id)
        if wid is not None and wid not in by_worker:
            raise ValueError('알 수 없는 작업자 ID')
        reasons = violations(by_worker[wid], state[wid], task) if wid is not None else []
        if wid is not None:
            apply(state[wid], task)
        rows.append(dict(task=task.id, worker=wid, violations=reasons))
    return dict(assignments=rows, states=state)


def metrics(result, tasks):
    by_task = {t.id: t for t in tasks}
    assigned = [r for r in result['assignments'] if r['worker'] is not None]
    states = list(result['states'].values())
    return {
        '배정 작업 수': len(assigned),
        '미배정 작업 수': len(tasks) - len(assigned),
        '배정 작업시간': round(sum(by_task[r['task']].duration for r in assigned), 2),
        '제약 위반 배정 수': sum(bool(r.get('violations')) for r in assigned),
        '최대 예상 피로': round(max((s['fatigue'] for s in states), default=0), 2),
        '최대 누적 부담': round(max((s['load'] for s in states), default=0), 2),
    }
