from http import HTTPStatus

"""
Um teste tem três passos - AAA

- Arange - Arranjo (Oque necessita para rodar)
- Act    - Executa
- Assert - Garanta que A é A

"""


def test_home(client):
    # Act
    response = client.get('/auth')

    # Assert
    assert response.json() == {'mensagem': 'Olá mundo!'}
    assert response.status_code == HTTPStatus.OK


def test_create_user(client):

    response = client.post(
        'auth/create_users',
        json={
            'email': 'teste@teste.com',
            'nome': 'Teste',
            'senha': '123456789',
            'is_ativo': True,
            'is_admin': True,
            'time': 'Teste',
        },
    )

    assert response.status_code == HTTPStatus.CREATED


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Testes de integração das rotas da API (camada HTTP). Sobem a aplicação
    via TestClient e validam status codes e respostas dos endpoints de
    '/auth'. Seguem o padrão AAA (Arrange, Act, Assert).

Imports:
    - http.HTTPStatus: comparar os status codes esperados (OK, CREATED).

Fixtures usadas (definidas em conftest.py):
    - client: TestClient da API, injetado como argumento nos testes.

Funções:
    - test_home(client): garante que GET '/auth' retorna 200 e a mensagem
      {'mensagem': 'Olá mundo!'}.
    - test_create_user(client): garante que POST '/auth/create_users' com um
      payload válido retorna 201 (CREATED).
==========================================================================
"""
