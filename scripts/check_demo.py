"""Static checks for the offline HTML demo bundle."""
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'demo'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value:
                self.targets.append((tag, value))


def check_file(path):
    parser = Links()
    text = path.read_text(encoding='utf-8')
    parser.feed(text)
    for _, target in parser.targets:
        parsed = urlparse(target)
        if parsed.scheme or parsed.netloc:
            raise ValueError(f'external HTML dependency: {path.name} -> {target}')
        if target.startswith('#'):
            continue
        target_path = (path.parent / target.split('#', 1)[0]).resolve()
        if not target_path.is_file() or DEMO not in target_path.parents:
            raise ValueError(f'missing local HTML target: {path.name} -> {target}')
    required = ('합성 데이터', '미검증 규칙')
    if not all(marker in text for marker in required):
        raise ValueError(f'missing simulation disclosure: {path.name}')
    if '<script src=' in text or '<link ' in text:
        raise ValueError(f'non-self-contained asset reference: {path.name}')
    return text


def check(root=ROOT):
    demo = root / 'demo'
    for name in ('index.html', 'PortSafeAX_allocation_demo.html', 'PortSafeAX_proximity_demo.html'):
        check_file(demo / name)
    allocation = json.loads((demo / 'PortSafeAX_allocation_demo.json').read_text(encoding='utf-8'))
    if set(allocation) != {'standard', 'shortage', 'fatigue'}:
        raise ValueError('allocation scenarios are incomplete')
    for name, record in allocation.items():
        if record.get('data_origin') != 'SIMULATED' or record.get('model_type') != 'UNVALIDATED_RULES':
            raise ValueError(f'bad allocation disclosure: {name}')
        if set(record.get('unassigned', {})) != {'groups', 'rows'}:
            raise ValueError(f'missing unassigned summary: {name}')
    proximity = json.loads((demo / 'PortSafeAX_proximity_demo.json').read_text(encoding='utf-8'))
    if len(proximity) != 8 or not all(item.get('data_origin') == 'SIMULATED' for item in proximity.values()):
        raise ValueError('proximity cases are incomplete or undisclosed')
    return True


if __name__ == '__main__':
    check()
    print('Static demo checks OK')
