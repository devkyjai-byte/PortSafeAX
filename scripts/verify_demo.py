"""Save reproducible scenario metrics alongside test evidence."""
import json
from pathlib import Path
from portsafe.synthetic import generate
from portsafe.engine import allocate, audit, metrics

results = {}
for scenario in ('standard', 'shortage', 'fatigue'):
    workers, tasks, baseline = generate(42, scenario)
    plan = allocate(workers, tasks)
    results[scenario] = {
        'before': metrics(audit(workers, tasks, baseline), tasks),
        'after': metrics(audit(workers, tasks, {r['task']: r['worker'] for r in plan['assignments']}), tasks),
    }
Path('data/verification_metrics.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(results, ensure_ascii=True))
