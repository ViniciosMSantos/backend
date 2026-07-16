from http import HTTPStatus

from fastapi.testclient import TestClient

from server.main import app

"""
Um teste tem três passos - AAA

- Arange - Arranjo (Oque necessita para rodar)
- Act    - Executa
- Assert - Garanta que A é A

"""


def test_home():
    # Arange
    cliente = TestClient(app)

    # Act
    response = cliente.get('/')

    # Assert
    assert response.json() == {'mensagem': 'Olá mundo!'}
    assert response.status_code == HTTPStatus.OK
