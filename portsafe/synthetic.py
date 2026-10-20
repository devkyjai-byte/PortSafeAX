"""Reproducible synthetic cases; no personal or field data."""
import argparse
import json
import random
from dataclasses import asdict
from pathlib import Path
from .engine import Worker, Task


def generate(seed=42, scenario='standard'):
    if scenario not in ('standard', 'shortage', 'fatigue'):
        raise ValueError('알 수 없는 시나리오')
    rng = random.Random(seed)
    workers = [Worker(f'W{i+1:02}', q, 2, 72 if scenario == 'fatigue' else 20 + i * 6, 50 + i * 10)
               for i, q in enumerate((('일반', '지게차'), ('일반',), ('일반', '크레인'), ('일반', '지게차'), ('일반', '크레인')))]
    if scenario == 'shortage':
        workers = workers[:2]
    tasks = [Task(f'T{i+1:02}', ('일반', '지게차', '크레인')[i % 3], rng.choice((.5, 1, 1.5)),
                  rng.randint(20, 90), rng.randint(20, 90), rng.randint(20, 90), rng.randint(20, 80), 1 + i % 3)
             for i in range(12)]
    # Intentionally imbalanced comparison, not a claim about real operations.
    baseline = {t.id: workers[i % min(2, len(workers))].id for i, t in enumerate(tasks)}
    return workers, tasks, baseline


def export(path, seed=42, scenario='standard'):
    workers, tasks, baseline = generate(seed, scenario)
    payload = dict(data_type='SYNTHETIC_DEMO', model_type='UNVALIDATED_RULES', seed=seed, scenario=scenario,
                   workers=[asdict(w) for w in workers], tasks=[asdict(t) for t in tasks], baseline=baseline)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--scenario', choices=['standard', 'shortage', 'fatigue'], default='standard')
    parser.add_argument('--output', default='data/synthetic_demo.json')
    args = parser.parse_args()
    export(args.output, args.seed, args.scenario)
