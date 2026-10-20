"""Offline evidence viewer generated from the existing allocation engine."""
import json
from dataclasses import asdict
from pathlib import Path
from portsafe.synthetic import generate
from portsafe.engine import allocate, allocate_reference, audit, metrics, score


def build():
    records = {}
    for key, title in [('standard','기본 작업배정'),('shortage','자격 인력 부족'),('fatigue','높은 초기 상태값')]:
        workers,tasks,baseline=generate(42,key)
        plan=allocate(workers,tasks)
        before=audit(workers,tasks,baseline)
        after=audit(workers,tasks,{r['task']:r['worker'] for r in plan['assignments']})
        reference=allocate_reference(workers,tasks)
        reference_audit=audit(workers,tasks,{r['task']:r['worker'] for r in reference['assignments']})
        records[key]=dict(title=title,version='allocation-evidence-0.1',data_origin='SIMULATED',
            model_type='UNVALIDATED_RULES',seed=42,workers=[asdict(w) for w in workers],
            tasks=[dict(asdict(t),score=score(t)) for t in tasks],baseline=baseline,
            plan=plan,before=metrics(before,tasks),after=metrics(after,tasks),
            before_states=before['states'],after_states=after['states'],
            reference=metrics(reference_audit,tasks),reference_plan=reference,
            comparison_note='동일 입력·작업 순서·제약. 단순안은 ID순 첫 적격자, 재배치안은 최대 상한 사용비율 최소 후보. 현장 방식이나 최적해를 대표하지 않음.')
    template=Path('scripts/allocation_viewer.html').read_text(encoding='utf-8')
    data=json.dumps(records,ensure_ascii=False,allow_nan=False)
    Path('demo/PortSafeAX_allocation_demo.html').write_text(template.replace('__DATA__',data.replace('<','\\u003c')),encoding='utf-8')
    Path('demo/PortSafeAX_allocation_demo.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Built 3 allocation scenarios')


if __name__=='__main__': build()
