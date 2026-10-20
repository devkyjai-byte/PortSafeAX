"""Future SafeBack integration boundary. No hardware integration is implemented."""
from typing import Protocol


class SafeBackSource(Protocol):
    def read_features(self, worker_id: str) -> dict:
        """Future consented, calibrated IMU/insole features; not a rule score."""
        ...


def connect_safeback():
    raise NotImplementedError('SafeBack IMU·인솔 연동은 후속 개발 범위입니다.')
