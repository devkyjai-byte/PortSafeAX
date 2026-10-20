from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_dashboard_all_scenarios():
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=30)
    assert not app.exception
    for case in ('rear', 'passing', 'blocked', 'stale'):
        app.selectbox(key='proximity_case').select(case).run(timeout=30)
        assert not app.exception
    assert '합성 데이터' in app.warning[0].value
    for scenario in ('shortage', 'fatigue', 'standard'):
        app.selectbox(key='allocation_scenario').select(scenario).run(timeout=30)
        assert not app.exception
        assert next(m.value for m in app.metric if m.label == '제약 위반 배정 수') == '0'
        groups = next(x.value for x in app.dataframe if '원인 구분' in x.value.columns and '미배정 작업 수' in x.value.columns)
        assert int(groups['미배정 작업 수'].sum()) == int(next(m.value for m in app.metric if m.label == '미배정 작업 수'))
    app.number_input[0].set_value(99).run(timeout=30)
    assert not app.exception


def test_review_form_and_snapshot_isolation():
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=30)
    identity = next(x.key.removeprefix('review_task_') for x in app.selectbox if x.key.startswith('review_task_'))
    app.text_area(key='review_reason_' + identity).set_value('합성 계획 조건 검토')
    next(x for x in app.button if x.label == '검토 기록 추가').click().run(timeout=30)
    assert not app.exception
    assert len(app.session_state['review_histories'][identity]) == 1
    assert app.session_state['review_histories'][identity][0]['execution_authorized'] is False
    assert next(m.value for m in app.metric if m.label == '검토 확인 작업') == '1'
    assert next(m.value for m in app.metric if m.label == '미검토 작업') == '11'
    app.selectbox(key='review_status_' + identity).select('보류')
    app.text_area(key='review_reason_' + identity).set_value('추가 검토 필요')
    next(x for x in app.button if x.label == '검토 기록 추가').click().run(timeout=30)
    assert next(m.value for m in app.metric if m.label == '검토 확인 작업') == '0'
    assert next(m.value for m in app.metric if m.label == '보류 작업') == '1'
    app.selectbox(key='review_filter_' + identity).select('보류').run(timeout=30)
    table = next(x.value for x in app.dataframe if '최신 검토 상태' in x.value.columns)
    assert len(table) == 1 and table.iloc[0]['최신 사유'] == '추가 검토 필요'
    app.number_input[0].set_value(99).run(timeout=30)
    other = next(x.key.removeprefix('review_task_') for x in app.selectbox if x.key.startswith('review_task_'))
    assert other != identity
    assert other not in app.session_state['review_histories']
    app.number_input[0].set_value(42).run(timeout=30)
    assert len(app.session_state['review_histories'][identity]) == 2
