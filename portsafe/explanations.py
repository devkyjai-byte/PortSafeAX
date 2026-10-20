"""Read-only explanations of allocator decisions at each task's decision time."""


def unassigned_summary(plan, tasks):
    by_task = {task.id: task for task in tasks}
    groups = {'후보 작업자 없음': 0, '필요 자격 충족 후보 없음': 0, '자격 충족 후보의 누적 상한 초과': 0}
    rows = []
    for decision in plan['assignments']:
        if decision['worker'] is not None:
            continue
        task = by_task[decision['task']]
        candidates = decision['rejected']
        qualified = {wid: reasons for wid, reasons in candidates.items() if '자격 불충족' not in reasons}
        if not candidates:
            category = '후보 작업자 없음'
            check = '해당 계획의 작업자 목록 입력 확인'
        elif not qualified:
            category = '필요 자격 충족 후보 없음'
            check = '작업의 필요 자격과 작업자 보유 자격 입력 확인'
        else:
            category = '자격 충족 후보의 누적 상한 초과'
            check = '자격 충족 후보의 누적 상태와 작업량 입력 확인'
        groups[category] += 1
        # Count each qualified candidate once per constraint. Counts may overlap.
        limits = {reason: sum(reason in reasons for reasons in qualified.values())
                  for reason in ('근무시간 상한 초과', '피로 상한 초과', '최대부하 상한 초과')}
        rows.append(dict(task_id=task.id, qualification=task.qualification,
                         priority=task.priority, duration_hours=task.duration,
                         category=category, candidate_count=len(candidates),
                         qualified_count=len(qualified), qualified_limit_counts=limits,
                         check=check))
    return dict(groups=groups, rows=rows)
