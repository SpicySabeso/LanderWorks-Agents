import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]  # dental-agent/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def test_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test_leads.db"

    # Parchea settings.DB_PATH si lo usas en store.enqueue_handoff
    from backend.config import settings

    monkeypatch.setattr(settings, "DB_PATH", str(db_path), raising=False)

    # Parchea la ruta DB_PATH del store si hace falta (según tu implementación)
    import backend.store as store

    monkeypatch.setattr(store, "DB_PATH", Path(db_path), raising=False)

    yield
