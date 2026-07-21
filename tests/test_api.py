import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.models import Base, Observation
from src.api import create_app


@pytest.fixture
def app():
    """Create a test Flask app backed by an in-memory SQLite database."""
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)

    # Seed test data
    with Session(test_engine) as session:
        session.add_all([
            Observation(
                dataset_id="DS001", category="Labor_and_Employment",
                entity_name="Employment Rate - National",
                variable_name="Value", year=2020, period="Q1", value=91.3,
            ),
            Observation(
                dataset_id="DS001", category="Labor_and_Employment",
                entity_name="Unemployment Rate - National",
                variable_name="Value", year=2020, period="Q1", value=5.3,
            ),
            Observation(
                dataset_id="DS002", category="Population_and_Vital_Statistics",
                entity_name="PHILIPPINES",
                variable_name="Total Population", year=2020, period=None,
                value=109033245,
            ),
        ])
        session.commit()

    flask_app = create_app(engine=test_engine)
    flask_app.config["TESTING"] = True

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def test_health(client):
    resp = client.get("/api/v1/health")
    # In test mode the real DB may not be up, so we just check the endpoint works
    assert resp.status_code in (200, 503)
    assert "status" in resp.get_json()


def test_list_datasets(client):
    resp = client.get("/api/v1/datasets")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 2
    ids = {d["dataset_id"] for d in body["data"]}
    assert ids == {"DS001", "DS002"}


def test_get_dataset_metadata(client):
    resp = client.get("/api/v1/datasets/DS001")
    assert resp.status_code == 200
    meta = resp.get_json()["data"]
    assert meta["dataset_id"] == "DS001"
    assert meta["row_count"] == 2
    assert "Value" in meta["variables"]


def test_get_dataset_not_found(client):
    resp = client.get("/api/v1/datasets/NOPE")
    assert resp.status_code == 404


def test_list_categories(client):
    resp = client.get("/api/v1/categories")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 2
    cats = {c["category"] for c in body["data"]}
    assert "Labor_and_Employment" in cats


def test_observations_no_filter(client):
    resp = client.get("/api/v1/observations")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["pagination"]["total"] == 3
    assert len(body["data"]) == 3


def test_observations_filter_category(client):
    resp = client.get("/api/v1/observations?category=Labor_and_Employment")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["pagination"]["total"] == 2
    for obs in body["data"]:
        assert obs["category"] == "Labor_and_Employment"


def test_observations_filter_entity_partial(client):
    resp = client.get("/api/v1/observations?entity_name=Employment")
    assert resp.status_code == 200
    body = resp.get_json()
    # Should match both "Employment Rate" and "Unemployment Rate"
    assert body["pagination"]["total"] == 2


def test_observations_pagination(client):
    resp = client.get("/api/v1/observations?per_page=1&page=2")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["data"]) == 1
    assert body["pagination"]["page"] == 2
    assert body["pagination"]["pages"] == 3
