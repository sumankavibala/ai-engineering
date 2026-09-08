import pytest
from app.main import app
from app.dependencies import get_current_user
from app.models.user import User

def test_employees_requires_auth(client):
    response = client.get("/employees/")
    assert response.status_code == 401

def test_create_employee_invalid_experience(client):
    def mock_get_current_user():
        return User(id=1, username="testuser", password_hash="hashed")

    app.dependency_overrides[get_current_user] = mock_get_current_user
    try:
        response = client.post(
            "/employees/",
            json={
                "name": "Suman",
                "role": "Developer",
                "experience": -1
            }
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()






#   import pytest
# from fastapi.testclient import TestClient

# from app.main import app
# from app.dependencies import get_current_user
# from app.models.user import User

# client = TestClient(app)


# @pytest.fixture(autouse=True)
# def override_current_user():
#     def mock_get_current_user():
#         return User(id=1, username="testuser", password_hash="hashed")

#     app.dependency_overrides[get_current_user] = mock_get_current_user
#     yield
#     app.dependency_overrides.clear()


# def test_get_employees():
#     response = client.get("/employees/")

#     assert response.status_code == 200