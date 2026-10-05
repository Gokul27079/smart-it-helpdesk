import pytest
from database.database import Database
from services.priority import detect_priority
from services.team_router import recommended_team
import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = Database(tmp_path / 'test.db')
    test_db.init_db()
    monkeypatch.setattr(app_module, 'db', test_db)
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as c:
        yield c


def payload(title='VPN is not connecting', description='My laptop cannot connect to the office VPN today.'):
    return {'title': title, 'description': description, 'user_name': 'Asha Rao', 'user_email': 'asha@example.com', 'department': 'Engineering'}


def test_priority_detection():
    priority, reason, matches = detect_priority('Possible ransomware attack detected on production')
    assert priority == 'Critical'
    assert matches
    assert 'critical' in reason.lower()


def test_team_recommendation():
    assert recommended_team('Network') == 'Network Support'
    assert recommended_team('Security') == 'Security Operations'


def test_classification_api(client):
    response = client.post('/api/classify', json={'title': 'VPN is not connecting', 'description': 'The VPN is not connecting from my laptop.'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['category'] == 'Network'
    assert 0 <= data['confidence'] <= 1
    assert data['recommended_team'] == 'Network Support'


def test_ticket_creation_and_database_insertion(client):
    response = client.post('/api/tickets', json=payload())
    assert response.status_code == 201
    data = response.get_json()
    assert data['ticket_id'].startswith('TKT-')
    assert data['category'] == 'Network'
    listed = client.get('/api/tickets').get_json()
    assert len(listed) == 1


def test_status_update_and_logs(client):
    created = client.post('/api/tickets', json=payload()).get_json()
    response = client.put(f"/api/tickets/{created['ticket_id']}", json={'status': 'In Progress'})
    assert response.status_code == 200
    assert response.get_json()['status'] == 'In Progress'
    detail = client.get(f"/api/tickets/{created['ticket_id']}").get_json()
    assert any(log['action'] == 'Status updated' for log in detail['logs'])


def test_validation_and_not_found(client):
    assert client.post('/api/tickets', json={'title': 'x'}).status_code == 400
    assert client.get('/api/tickets/TKT-99999').status_code == 404
    assert client.put('/api/tickets/TKT-99999', json={'status': 'Broken'}).status_code == 400


def test_delete_ticket(client):
    created = client.post('/api/tickets', json=payload()).get_json()
    assert client.delete(f"/api/tickets/{created['ticket_id']}").status_code == 200
    assert client.get(f"/api/tickets/{created['ticket_id']}").status_code == 404
