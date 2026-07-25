from http import HTTPStatus

"""
Um teste tem três passos - AAA

- Arange - Arranjo (Oque necessita para rodar)
- Act    - Executa
- Assert - Garanta que A é A

"""


def test_home(client):
    """
    POR QUE ESTE TESTE EXISTE:
    É o "smoke test" da API — o mais barato de todos. Se ele falhar,
    a aplicação nem sobe (erro de import, router não registrado,
    prefixo errado) e não adianta investigar os outros testes.

    Arrange: não há arranjo aqui; o `client` já chega pronto da
    fixture do conftest.py.

    Act: requisição HTTP real, porém em memória (sem servidor).
    """

    response = client.get('/auth')

    # Assert: dois checks complementares —
    # o CORPO garante que a rota certa respondeu...
    assert response.json() == {'mensagem': 'Olá mundo!'}
    # ...e o STATUS garante que respondeu com sucesso. HTTPStatus.OK é
    # usado no lugar do número 200 por legibilidade.
    assert response.status_code == HTTPStatus.OK


def test_create_user(client):
    """
    POR QUE ESTE TESTE EXISTE:
    Cobre o caminho feliz do cadastro pela API (contrato HTTP):
    payload válido -> o schema Pydantic aceita -> a rota grava o
    usuário -> retorna 201. Diferente do test_db.py, aqui o que
    importa é o CONTRATO da rota, não o ORM.

    Act: POST com o JSON no formato que o schema de entrada espera.
    Se algum nome de campo mudar no Pydantic, a API devolve 422 e
    este teste acusa a quebra de contrato.
    """
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

    # Assert: 201 CREATED (e não 200) é o status semanticamente correto
    # para criação de recurso — o teste também protege essa escolha.
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
