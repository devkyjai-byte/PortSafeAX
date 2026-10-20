from portsafe.engine import allocate, allocate_reference, audit, Worker, Task
from portsafe.synthetic import generate


def test_reference_constraints_order_and_reproducibility():
    for scenario in ('standard', 'shortage', 'fatigue'):
        for seed in range(100):
            workers, tasks, _ = generate(seed, scenario)
            ref = allocate_reference(workers, tasks)
            assert ref == allocate_reference(list(reversed(workers)), tasks)
            assert [r['task'] for r in ref['assignments']] == [r['task'] for r in allocate(workers, tasks)['assignments']]
            checked = audit(workers, tasks, {r['task']:r['worker'] for r in ref['assignments']})
            assert all(not row['violations'] for row in checked['assignments'])


def test_reference_first_eligible_and_impossible():
    workers = [Worker('B', ('general',), 0, 0, 0), Worker('A', ('general',), 0, 0, 0)]
    tasks = [Task('T1', 'general', 1, 0, 0, 0, 0), Task('T2', 'crane', 1, 0, 0, 0, 0)]
    result = allocate_reference(workers, tasks)
    assert result['assignments'][0]['worker'] == 'A'
    assert result['assignments'][1]['worker'] is None
    assert all(allocate_reference([], tasks)['assignments'][i]['worker'] is None for i in range(2))
