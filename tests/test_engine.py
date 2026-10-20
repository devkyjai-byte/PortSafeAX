import math
import pytest
from portsafe.engine import Worker, Task, score, allocate, audit, metrics
from portsafe.synthetic import generate, export


def worker(**kw):
    return Worker(**(dict(id='W', qualifications=('Q',), hours=0, fatigue=0, load=0) | kw))


def task(**kw):
    return Task(**(dict(id='T', qualification='Q', duration=1, weight=100, repetition=100, posture=100, heat=100) | kw))


def test_score_endpoints_and_weights():
    assert score(task()) == 100
    assert score(task(weight=0, repetition=0, posture=0, heat=0)) == 0
    assert score(task(weight=100, repetition=0, posture=0, heat=0)) == 35


@pytest.mark.parametrize('change,reason', [({'qualifications': ()}, '자격'), ({'max_hours': .5}, '근무시간'), ({'max_fatigue': 11}, '피로'), ({'max_load': 99}, '최대부하')])
def test_each_constraint(change, reason):
    result = allocate([worker(**change)], [task()])
    row = result['assignments'][0]
    assert row['worker'] is None
    assert any(reason in r for r in row['rejected']['W'])
    assert result['states']['W']['load'] == 0


def test_exact_limits_and_cumulative_rejection():
    w = worker(max_hours=1, max_fatigue=12, max_load=100)
    result = allocate([w], [task(), task(id='U')])
    assert [r['worker'] for r in result['assignments']] == ['W', None]


def test_priority_is_respected():
    result = allocate([worker(max_hours=1)], [task(id='A'), task(id='Z', priority=3)])
    assert result['assignments'][0]['task'] == 'Z'
    assert result['assignments'][0]['worker'] == 'W'


def test_invalid_inputs_and_duplicates():
    for value in (math.nan, math.inf, -1, 101, True):
        with pytest.raises(ValueError):
            task(weight=value)
    with pytest.raises(ValueError):
        task(duration=0)
    with pytest.raises(ValueError):
        allocate([worker(), worker()], [])
    with pytest.raises(ValueError):
        allocate([], [task(), task()])
    with pytest.raises(ValueError):
        audit([worker()], [task()], {'T': 'missing'})


def test_empty_and_initially_over_limit():
    assert allocate([], [task()])['assignments'][0]['worker'] is None
    assert allocate([worker(hours=9)], [task()])['assignments'][0]['worker'] is None
    assert metrics(allocate([], []), [])['배정 작업 수'] == 0


@pytest.mark.parametrize('scenario', ['standard', 'shortage', 'fatigue'])
def test_synthetic_safety_over_many_seeds(scenario):
    for seed in range(100):
        workers, tasks, baseline = generate(seed, scenario)
        result = allocate(workers, tasks)
        assert result == allocate(workers, tasks)
        rows = result['assignments']
        assert len(rows) == len(tasks)
        checked = audit(workers, tasks, {r['task']: r['worker'] for r in rows})
        assert metrics(checked, tasks)['제약 위반 배정 수'] == 0
        for w in workers:
            for key in ('hours', 'fatigue', 'load'):
                assert result['states'][w.id][key] <= getattr(w, 'max_' + key) + 1e-9


def test_export_and_reproducibility(tmp_path):
    import json
    assert generate(42) == generate(42)
    assert generate(42) != generate(43)
    out = tmp_path / 'demo.json'
    export(out)
    assert json.loads(out.read_text(encoding='utf-8'))['data_type'] == 'SYNTHETIC_DEMO'


def test_baseline_reports_violations():
    workers, tasks, baseline = generate()
    assert metrics(audit(workers, tasks, baseline), tasks)['제약 위반 배정 수'] > 0
