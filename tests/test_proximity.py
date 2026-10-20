import math
import pytest
from portsafe.proximity import Sample, evaluate, reports


@pytest.mark.parametrize('key', ['front', 'rear', 'crossing', 'near_static'])
def test_approach_and_existing_zone_warn(key):
    assert reports()[key]['status'] == 'ALERT'


@pytest.mark.parametrize('key', ['passing', 'receding'])
def test_non_intersecting_paths_not_alerted(key):
    assert reports()[key]['status'] == 'NO_ALERT'


@pytest.mark.parametrize('sample', [Sample(0, 10, 0, -2, 'blocked'), Sample(0, 10, 0, -2, age=2),
                                  Sample(math.nan, 1, 0, 0), Sample(0, 1, math.inf, 0),
                                  Sample(0, 1, 0, 0, age=-1)])
def test_bad_observation_never_reported_as_clear(sample):
    result = evaluate(sample)
    assert result['status'] == 'UNKNOWN'
    assert result['distance_m'] is None
    assert result['alert_entry_s'] is None


def test_zone_boundary_and_horizon():
    assert evaluate(Sample(2, 0, 0, 0))['status'] == 'ALERT'
    assert evaluate(Sample(2.01, 0, 0, 0))['status'] == 'NO_ALERT'
    assert evaluate(Sample(0, 14, 0, -2))['alert_entry_s'] == 6
    assert evaluate(Sample(0, 14.01, 0, -2))['status'] == 'NO_ALERT'


def test_crossing_not_dependent_on_initial_radial_ttc():
    # Six seconds to closest approach but a miss, vs crossing the circular zone.
    miss = evaluate(Sample(5, 10, 0, -2))
    hit = evaluate(Sample(0, 10, 0, -2))
    assert miss['closest_distance_m'] == 5
    assert hit['alert_entry_s'] == 4
    assert hit['closest_time_s'] == 5


def test_rotation_preserves_zone_entry():
    a = evaluate(Sample(0, 10, 0, -2))
    b = evaluate(Sample(10, 0, -2, 0))
    assert a['alert_entry_s'] == b['alert_entry_s']
    assert a['direction'] == '전방' and b['direction'] == '우측'
