"""Fixtures compartidos para los tests del microservicio de Notificaciones."""

import pytest
from unittest.mock import MagicMock


class FakeDB:
    def __init__(self):
        self._cols = {"estados": MagicMock()}

    def __getitem__(self, name):
        return self._cols[name]


@pytest.fixture
def fake_db():
    return FakeDB()
