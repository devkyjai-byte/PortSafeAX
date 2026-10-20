import json
from dataclasses import asdict
import pandas as pd
import streamlit as st
from portsafe.engine import allocate, audit, metrics, score, apply, increment, initial, validate, violations
try:
    from portsafe.engine import allocate_reference
except ImportError:
    # Compatibility path for an older cached engine module. The current engine
    # provides the deterministic ID-order reference allocator directly.
    def allocate_reference(workers, tasks):
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
from portsafe.synthetic import generate
from portsafe.explanations import unassigned_summary
from portsafe.proximity import CASES, evaluate
from portsafe.review import snapshot_id, record_review, export_reviews, restore_reviews, review_summary, MAX_REVIEW_BYTES

st.set_page_config(page_title='PortSafe AX | 합성 데이터 시연', page_icon='⚓', layout='wide')
st.title('⚓ PortSafe AX')
st.caption('안전 제약조건 기반 작업 재배치 · 공모전 시연 MVP')
st.warning('합성 데이터 시연입니다. 작업부담·피로는 검증되지 않은 규칙 계산값이며, ML 예측·의학적 판정·실제 사고 감소 성능을 의미하지 않습니다.')
with st.sidebar:
    st.header('시연 설정')
    scenario = st.selectbox('시나리오', ['standard', 'shortage', 'fatigue'], format_func=lambda x: {'standard':'기본 작업 재배치', 'shortage':'자격 인력 부족', 'fatigue':'높은 초기 피로'}[x], key='allocation_scenario')
    seed = st.number_input('합성 데이터 시드', 0, 999999, 42)
    st.caption('설정을 바꾸면 동일한 규칙으로 즉시 다시 계산합니다.')
    st.info('SafeBack IMU·인솔: 미연동 / 후속 모듈')

workers, tasks, baseline = generate(int(seed), scenario)
before = audit(workers, tasks, baseline)
plan = allocate(workers, tasks)
mapping = {r['task']: r['worker'] for r in plan['assignments']}
after = audit(workers, tasks, mapping)
bm, am = metrics(before, tasks), metrics(after, tasks)
tabs = st.tabs(['대시보드', '배정·미배정 사유', '입력·점수 설명', '시연·한계', '접근 경고 연구 시연', '관리자 검토 기록'])
with tabs[0]:
    st.subheader('재배치 전후 시뮬레이션')
    st.caption('비교 기준은 의도적으로 두 작업자에게 집중 배정한 합성 예시입니다. 두 안의 완료 작업량이 다를 수 있습니다.')
    cols = st.columns(3)
    for col, key in zip(cols, ['배정 작업 수', '미배정 작업 수', '제약 위반 배정 수']):
        col.metric(key, am[key], f'이전 {bm[key]}', delta_color='off')
    comparison = pd.DataFrame({'이전': bm, '재배치 후': am})
    st.dataframe(comparison, use_container_width=True)
    chart = pd.DataFrame({'이전': {k:v['load'] for k,v in before['states'].items()}, '재배치 후': {k:v['load'] for k,v in after['states'].items()}})
    st.bar_chart(chart)
    st.caption('누적 부담 단위: 규칙 점수 × 시간. 배정 감소에 따른 수치 감소를 개선율로 표시하지 않습니다.')
    st.subheader('동일 제약을 적용한 단순 배정안과 비교')
    reference = allocate_reference(workers, tasks)
    reference_audit = audit(workers, tasks, {r['task']: r['worker'] for r in reference['assignments']})
    reference_metrics = metrics(reference_audit, tasks)
    st.dataframe(pd.DataFrame({'ID순 단순 배정': reference_metrics, '재배치안': am}), use_container_width=True)
    st.caption('같은 입력·작업 처리 순서·자격·상한을 적용합니다. 단순안은 ID순 첫 적격자를 선택합니다. 실제 현장 방식이 아니며 재배치안의 우수성이나 최적성을 보장하지 않습니다.')
    report = dict(data_type='SYNTHETIC_DEMO', model_type='UNVALIDATED_RULES', seed=int(seed), scenario=scenario,
                  before=bm, after=am, plan=plan, reference=reference_metrics, reference_plan=reference,
                  workers=[asdict(w) for w in workers], tasks=[asdict(t) for t in tasks], baseline=baseline)
    st.download_button('시연 결과 JSON 다운로드', json.dumps(report, ensure_ascii=False, indent=2), 'portsafe_demo_report.json', 'application/json')
with tabs[1]:
    st.subheader('미배정 원인 요약')
    pending = unassigned_summary(plan, tasks)
    st.dataframe(pd.DataFrame([{'원인 구분': category, '미배정 작업 수': count}
                               for category, count in pending['groups'].items()]), hide_index=True)
    if pending['rows']:
        st.dataframe(pd.DataFrame([{
            '작업': row['task_id'], '필요 자격': row['qualification'],
            '우선순위(3이 먼저)': row['priority'], '작업시간(시간)': row['duration_hours'],
            '원인 구분': row['category'], '전체 후보 수': row['candidate_count'],
            '자격 충족 후보 수': row['qualified_count'],
            '시간 초과 후보 수': row['qualified_limit_counts']['근무시간 상한 초과'],
            '피로 초과 후보 수': row['qualified_limit_counts']['피로 상한 초과'],
            '부담 초과 후보 수': row['qualified_limit_counts']['최대부하 상한 초과'],
            '관리자 입력 확인 항목': row['check']
        } for row in pending['rows']]), hide_index=True)
    else:
        st.info('현재 계산에서 미배정 작업은 없습니다. 실제 현장 안전을 확인한 결과는 아닙니다.')
    st.caption('작업별 배정 판단 시점의 후보 사유를 집계합니다. 상한 초과 후보 수는 자격 충족 후보만 대상으로 하며 한 사람이 여러 상한에 중복 집계될 수 있습니다. 원인 구분별 작업 수는 중복되지 않습니다. 입력 확인 항목은 배정 가능성 보장이나 상한 완화 지시가 아닙니다.')
    st.subheader('작업별 제안과 제약조건 확인')
    st.dataframe(pd.DataFrame([{'작업': r['task'], '배정 작업자': r['worker'] or '미배정', '결과': r['reason']} for r in plan['assignments']]), hide_index=True, use_container_width=True)
    for row in plan['assignments']:
        with st.expander(f"{row['task']} → {row['worker'] or '미배정'} · 후보별 확인"):
            st.json({wid: reasons or ['제약 충족'] for wid, reasons in row['rejected'].items()})
    st.caption('후보 사유는 해당 작업을 검토한 시점의 누적 상태입니다. 미배정 작업은 관리자 확인 후 인력 확보·휴식·작업 연기를 검토해야 합니다.')
with tabs[2]:
    st.subheader('합성 작업자')
    st.dataframe(pd.DataFrame([asdict(w) for w in workers]), hide_index=True)
    st.subheader('합성 작업과 규칙 점수')
    st.dataframe(pd.DataFrame([dict(asdict(t), burden_score=score(t)) for t in tasks]), hide_index=True)
    st.markdown('작업부담 점수 = 중량지수 × 0.35 + 반복지수 × 0.25 + 자세지수 × 0.25 + 열환경지수 × 0.15. 모든 입력은 0~100의 가상 지수입니다. kg·온도 실측값이 아닙니다.')
    st.markdown('추가 부담 = 점수 × 작업시간. 추가 피로 = 추가 부담 × 0.12. 가중치·상한·피로 계수는 시연용 가정이며 현장 검증이 필요합니다.')
with tabs[3]:
    st.markdown('''### 3분 시연
1. 기본 시나리오에서 전후 배정량과 제약 위반 수를 확인합니다.
2. 배정·미배정 사유에서 자격과 누적 상한 검사를 설명합니다.
3. 자격 인력 부족·높은 초기 피로 시나리오로 전환해 미배정을 확인합니다.
4. 결과 JSON을 내려받아 계산 근거를 보관합니다.

### 적용 범위
동일 계획 구간에서 작업자가 작업을 순차 수행하는 가정입니다. 시간대별 일정·휴식 회복·동시 작업·이동·장비 가용성은 모델링하지 않습니다. 탐욕적 휴리스틱이므로 최적 배정이나 최대 처리량을 보장하지 않습니다. 실제 배치 전 관리자 검토와 현장 검증이 필요합니다.

### 개발 단계
Phase 1: 규칙·데이터·제약 설계 → Phase 2: 엔진·테스트 → Phase 3: 대시보드·시연.
검증된 ML 모델은 포함하지 않습니다. SafeBack 센서는 별도 후속 모듈입니다.
''')
with tabs[4]:
    st.subheader('주변 접근 경고 — 합성 사례 탐색')
    st.warning('실제 카메라·레이더 미연결. 정확한 상대 위치·속도를 가정한 규칙 시연이며 센서 성능 또는 현장 안전 검증이 아닙니다.')
    case = st.selectbox('접근 상황', list(CASES), format_func=lambda k: CASES[k][0], key='proximity_case')
    result = evaluate(CASES[case][1])
    st.write(result['label'])
    st.write(result['reason'])
    st.caption('2m 경계·6초 예측 구간·관측 유효시간0.5초는 설명용 가정입니다. 차량 크기·제동·가림·선회는 모델링하지 않습니다.')
    if result['status'] != 'UNKNOWN':
        st.write({'물체 방향': result['direction'], '현재 거리(m)': result['distance_m'],
                  '시연 경계 진입시간(초)': result['alert_entry_s']})
    st.caption('경고 조건 미충족은 안전 확인이 아닙니다. 작업부담 점수·재배치 결과에는 합산하지 않습니다.')
    st.download_button('접근 사례 JSON 다운로드', json.dumps(result, ensure_ascii=False, indent=2),
                       'portsafe_proximity_SIMULATED.json', 'application/json')
with tabs[5]:
    st.subheader('관리자 검토 기록 — 합성 시연')
    st.info('검토 메모이며 작업 승인·배치 명령이 아닙니다. 배정 결과와 제약을 변경하지 않습니다.')
    st.caption('기록은 현재 브라우저 연결 세션에만 보관됩니다. 새로고침·연결 종료 시 사라질 수 있으므로 JSON을 내려받으세요. 실명·건강정보를 입력하지 마세요. 사용자 인증·변조 방지 감사 기능은 없습니다.')
    identity = snapshot_id(report)
    all_reviews = st.session_state.setdefault('review_histories', {})
    history = all_reviews.get(identity, [])
    with st.expander('저장한 검토 기록 불러오기'):
        st.caption('현재와 같은 시나리오·시드·계획의 검토 JSON만 복원합니다. 기존 기록과 충돌하면 덮어쓰지 않습니다. 파일은 작성자 인증 자료가 아니며 실제 승인을 의미하지 않습니다.')
        uploaded = st.file_uploader('검토 이력 JSON 선택 (최대 2MB)', type=['json'], key='review_upload_' + identity)
        if st.button('검토 기록 복원', key='review_restore_' + identity, disabled=uploaded is None):
            try:
                if uploaded.size > MAX_REVIEW_BYTES:
                    raise ValueError('2MB 이하의 JSON 파일을 선택하세요.')
                restored = restore_reviews(report, history, uploaded.getvalue())
                added = len(restored) - len(history)
                history = restored
                all_reviews[identity] = history
                st.success(f'검토 기록 {added}건을 복원했습니다. 기존 중복 기록과 배정 결과는 변경하지 않았습니다.')
            except ValueError as exc:
                st.error(str(exc))
    with st.form('review_form_' + identity):
        selected_task = st.selectbox('검토할 작업', [r['task'] for r in plan['assignments']], key='review_task_' + identity)
        review_status = st.selectbox('검토 상태', ['검토 확인', '보류', '입력 정정 요청'], key='review_status_' + identity)
        reason = st.text_area('검토 사유', max_chars=500, key='review_reason_' + identity)
        submitted = st.form_submit_button('검토 기록 추가')
    if submitted:
        try:
            history = record_review(report, history, selected_task, review_status, reason)
            all_reviews[identity] = history
            st.success('현재 입력·계획에 연결된 검토 기록을 추가했습니다. 실제 배정은 변경하지 않았습니다.')
        except ValueError as exc:
            st.error(str(exc))
    st.subheader('작업별 최신 검토 상태')
    overview = review_summary(report, history)
    review_cols = st.columns(4)
    for col, (status, count) in zip(review_cols, overview['counts'].items()):
        col.metric(status + ' 작업', count)
    st.caption(f"추가 확인 대상 {overview['needs_review']}건. 작업별 마지막으로 추가한 기록을 표시합니다. ‘검토 확인’은 작업 승인·안전 확인·실제 작업 완료가 아닙니다.")
    review_filter = st.selectbox('표시할 검토 상태', ['확인 필요', '전체', *overview['counts']],
                                 key='review_filter_' + identity)
    visible = [row for row in overview['rows'] if review_filter == '전체'
               or (review_filter == '확인 필요' and row['status'] != '검토 확인')
               or row['status'] == review_filter]
    if visible:
        st.dataframe(pd.DataFrame([{'작업': row['task_id'], '배정 작업자': row['assigned_worker'] or '미배정',
                                   '최신 검토 상태': row['status'], '최신 사유': row['reason'],
                                   '기록 순번': row['sequence'], '기록 시각(UTC)': row['timestamp_utc']}
                                  for row in visible]), hide_index=True)
    else:
        st.info('선택한 상태의 작업이 없습니다. 배정 결과나 실제 현장 안전 여부를 뜻하지 않습니다.')
    if history:
        st.subheader('전체 검토 이력')
        st.dataframe(pd.DataFrame(history)[['sequence', 'timestamp_utc', 'task_id', 'assigned_worker', 'status', 'reason']], hide_index=True)
        st.download_button('검토 이력과 계획 JSON 다운로드',
            export_reviews(report, history),
            'portsafe_review_SIMULATED.json', 'application/json')
    else:
        st.write('현재 입력·계획에 대한 검토 기록이 없습니다.')
    st.caption('시나리오·시드 또는 계획 내용이 달라지면 별도 기록으로 구분합니다. 변경 이력은 덮어쓰지 않고 시간순으로 추가합니다. 입력 정정 요청은 메모이며 입력 수정 기능은 아직 없습니다.')
