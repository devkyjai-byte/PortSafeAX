from copy import deepcopy

import pytest

from portsafe.engine import Worker, Task, allocate
from portsafe.explanations import unassigned_summary
from portsafe.synthetic import generate


def task():
    return Task('T', 'Q', 1, 100, 100, 100, 100)


def test_no_candidates_and_no_qualified_candidates_are_distinct():
    t = task()
    empty = unassigned_summary(allocate([], [t]), [t])
    assert empty['groups']['후보 작업자 없음'] == 1
    workers = [Worker('W', (), 8, 80, 300)]
    summary = unassigned_summary(allocate(workers, [t]), [t])
    row = summary['rows'][0]
    assert row['category'] == '필요 자격 충족 후보 없음'
    assert row['qualified_count'] == 0
    assert all(count == 0 for count in row['qualified_limit_counts'].values())


def test_limit_counts_overlap_only_for_qualified_candidates():
    workers = [Worker('A', ('Q',), 8, 80, 300), Worker('B', (), 8, 80, 300)]
    t = task(); plan = allocate(workers, [t]); saved = deepcopy(plan)
    summary = unassigned_summary(plan, [t]); row = summary['rows'][0]
    assert row['category'] == '자격 충족 후보의 누적 상한 초과'
    assert row['candidate_count'] == 2 and row['qualified_count'] == 1
    assert list(row['qualified_limit_counts'].values()) == [1, 1, 1]
    assert plan == saved


@pytest.mark.parametrize('scenario', ['standard', 'shortage', 'fatigue'])
def test_groups_cover_each_unassigned_task_exactly_once(scenario):
    workers, tasks, _ = generate(42, scenario)
    plan = allocate(workers, tasks)
    summary = unassigned_summary(plan, tasks)
    unassigned = [row['task'] for row in plan['assignments'] if row['worker'] is None]
    assert [row['task_id'] for row in summary['rows']] == unassigned
    assert sum(summary['groups'].values()) == len(unassigned)
