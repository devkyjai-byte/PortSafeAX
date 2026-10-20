"""Export precomputed synthetic scenarios to a self-contained, offline HTML."""
import json
from pathlib import Path
from portsafe.proximity import reports


def build():
    payload = json.dumps(reports(), ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    template = '''<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PortSafe AX · 접근 경고 연구 시연</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#edf2f6;color:#172d40;font:17px/1.65 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:32px 20px}h1{font-size:32px;margin:0}h2{font-size:22px}.muted{color:#405b6d}.notice{background:#fff2cb;border-left:5px solid #ad6800;padding:16px;margin:20px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.card{background:white;border:1px solid #ced9e2;border-radius:12px;padding:22px}select,button{font:inherit;padding:10px;border:1px solid #8da4b5;border-radius:6px;background:white;max-width:100%}button{cursor:pointer;margin-top:20px}.status{font-weight:700;font-size:22px;padding:14px;background:#e7edf3}.ALERT{background:#ffe4d6;color:#842d05}.UNKNOWN{background:#fff0c2;color:#694400}svg{width:100%;max-height:400px}dt{font-weight:700}dd{margin:0 0 12px}summary{cursor:pointer}footer{margin:24px 0}.legend{font-size:14px}@media(max-width:720px){.grid{grid-template-columns:1fr}h1{font-size:26px}}
</style><main>
<p class="muted">PORTSAFE AX / 연구 시연 0.1</p><h1>주변 접근 경고는 어떻게 판단할까요?</h1>
<div class="notice"><strong>합성 데이터 · 미검증 규칙 · 실제 센서 미연결</strong><br>사전 계산한 사례를 탐색하는 시연입니다. 카메라 인식, 레이더 검출, AI 성능 또는 현장 안전성을 검증한 자료가 아닙니다.</div>
<label for="scenario">검토할 상황 </label><select id="scenario"></select>
<div class="grid" style="margin-top:20px"><section class="card"><h2>위에서 본 상대 위치</h2>
<svg viewBox="0 0 360 360" role="img" aria-label="작업자와 합성 물체의 상대 위치 및 예상 경로">
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="#b34317"/></marker></defs>
<path d="M20 180H340 M180 20V340" stroke="#a9bac8" stroke-dasharray="4"/>
<circle cx="180" cy="180" r="24" fill="#ffeed6" stroke="#c27310" stroke-dasharray="4"/>
<circle cx="180" cy="180" r="8" fill="#146377"/><text x="193" y="200" font-size="13">작업자</text>
<text x="165" y="18">전방</text><text x="165" y="350">후방</text><text x="5" y="170">좌</text><text x="335" y="170">우</text>
<line id="path" stroke="#b34317" stroke-width="3" marker-end="url(#arrow)"/>
<circle id="object" r="7" fill="#b34317"/>
<text id="unknown" x="180" y="100" text-anchor="middle" fill="#694400" font-size="18"></text>
</svg><p class="legend">점선 원: 가정한 2m 경계 / 화살표: 최대6초의 일정 상대속도 경로. 차량 크기·선회는 반영하지 않습니다. 이 원은 실제 안전거리가 아닙니다.</p></section>
<section class="card" aria-live="polite"><h2 id="title"></h2><div id="status" class="status"></div><p id="reason"></p><dl id="details"></dl><button id="download">이 사례 결과 내려받기</button></section></div>
<section class="card" style="margin-top:20px"><h2>이 시연에서 확인하는 것</h2><p>정면·후면·측면 접근과 옆으로 지나가는 경우를 구분합니다. 센서 가림이나 오래된 관측은 “경고 없음”이 아닌 “판단 불가”로 표시합니다. 경고 방향은 위험 물체 방향이며 회피 방향 지시가 아닙니다.</p>
<details><summary>가정과 실제 검증이 필요한 항목</summary><p>상대 위치와 2차원 상대속도를 정확히 안다고 가정합니다. 실제 레이더는 이 값을 그대로 제공하지 않으며 추적·좌표 변환·자기 움직임 보정이 필요합니다. 카메라/레이더 시야·가림·금속 반사·간섭·오경보·지연·배터리는 이 시연으로 검증되지 않습니다. 2m·6초·관측 유효시간0.5초는 설명용 값이며 안전 기준이 아닙니다. 센서가 고장 난 사례의 위치·경로는 숨깁니다.</p></details></section>
<footer class="muted">SmokeFree AI와 독립된 PortSafe AX 연구 시연 · SafeBack은 별도 후속 확장 · 실제 장비 제어 없음</footer>
</main><script>
const reports=__DATA__;const select=document.getElementById('scenario');
for(const [key,r] of Object.entries(reports)){const opt=document.createElement('option');opt.value=key;opt.textContent=r.title;select.appendChild(opt)}
function render(){const r=reports[select.value];document.getElementById('title').textContent=r.title;
const status=document.getElementById('status');status.className='status '+r.status;status.textContent=r.label;
document.getElementById('reason').textContent=r.reason;const dl=document.getElementById('details');dl.replaceChildren();
const rows=[['물체 방향',r.direction??'판단 불가'],['현재 거리',r.distance_m===null?'판단 불가':r.distance_m.toFixed(1)+'m'],['가정 경계까지 진입시간',r.alert_entry_s===null?'해당 없음 / 판단 불가':r.alert_entry_s.toFixed(1)+'초']];
for(const [k,v] of rows){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=k;dd.textContent=v;dl.append(dt,dd)}
const ok=r.status!=='UNKNOWN',p=r.input;const line=document.getElementById('path'),obj=document.getElementById('object');line.style.display=obj.style.display=ok?'':'none';document.getElementById('unknown').textContent=ok?'':'관측 신뢰 불가 · 경로 숨김';
if(ok){obj.setAttribute('cx',180+p.x*12);obj.setAttribute('cy',180-p.y*12);line.setAttribute('x1',180+p.x*12);line.setAttribute('y1',180-p.y*12);line.setAttribute('x2',180+(p.x+p.vx*6)*12);line.setAttribute('y2',180-(p.y+p.vy*6)*12)}}
select.addEventListener('change',render);document.getElementById('download').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(reports[select.value],null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='portsafe_'+select.value+'_SIMULATED.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});render();
</script></html>'''
    output = Path('demo/PortSafeAX_proximity_demo.html')
    output.parent.mkdir(exist_ok=True)
    output.write_text(template.replace('__DATA__', payload), encoding='utf-8')
    output.with_suffix('.json').write_text(json.dumps(reports(), ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(output.resolve())


if __name__ == '__main__':
    build()
