"""Fixtures compartidos para los tests del microservicio de Notificaciones."""

from unittest.mock import MagicMock

import pytest


class FakeDB:
    def __init__(self):
        self._cols = {"estados": MagicMock()}

    def __getitem__(self, name):
        return self._cols[name]


@pytest.fixture
def fake_db():
    return FakeDB()
