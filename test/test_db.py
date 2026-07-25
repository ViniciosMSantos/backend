from dataclasses import asdict
from datetime import datetime

from sqlalchemy import select

from server.database.models import User


def test_create_user(session, return_mock):
    """POR QUE ESTE TESTE EXISTE.

    Valida o modelo User no nível do ORM — sem passar pela API. Prova
    que o mapeamento está correto: as colunas existem, o INSERT
    funciona e os campos gerados pelo banco (user_id, created_at) são
    preenchidos como esperado. Se o modelo quebrar, este teste falha
    antes dos testes de rota, deixando claro onde está o problema.
    `session` e `return_mock` vêm do conftest.py — o pytest injeta as
    fixtures pelo NOME do parâmetro, não é preciso importar nada.
    Congela o created_at durante o bloco. datetime.now() é capturado
    UMA vez e reaproveitado no assert como `time_mock`, então o valor
    comparado é exatamente o que foi gravado.
    """
    with return_mock(model=User, time=datetime.now()) as time_mock:
        # Arrange: monta o objeto em memória. Ainda não há SQL aqui.
        user = User(
            user_email='teste@teste.com',
            user_name='teste',
            user_password='teste',
            is_ativo=True,
            is_admin=True,
            user_time='Teste',
        )

        # Act: add() coloca o objeto na fila da sessão (pendente) e
        # commit() é quem de fato dispara o INSERT no banco.
        session.add(user)
        session.commit()

        # Relê do banco em vez de confiar no objeto em memória. Só
        # assim testamos o que o banco realmente gravou/gerou.
        # scalar() devolve o primeiro objeto (ou None), não uma tupla.
        user = session.scalar(select(User).where(User.user_name == 'teste'))

    # Assert fora do `with`: o listener já foi removido, provando que o
    # dado ficou persistido e não depende mais do mock.
    # asdict() só funciona porque User é mapeado como dataclass —
    # permite comparar o registro INTEIRO de uma vez, o que também pega
    # colunas novas que alguém adicione ao modelo sem atualizar o teste.
    assert asdict(user) == {
        'user_id': 1,
        'user_email': 'teste@teste.com',
        'user_name': 'teste',
        'user_password': 'teste',
        'is_ativo': True,
        'is_admin': True,
        'user_time': 'Teste',
        'created_at': time_mock,
    }


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Testes da camada de dados (ORM), sem passar pela API. Gravam um registro
    de verdade em um SQLite em memória, leem de volta e conferem TODAS as
    colunas — inclusive as preenchidas pelo banco (user_id e created_at).

Imports:
    - dataclasses.asdict: converte o User (mapeado como dataclass) em dict
      para comparar o registro inteiro de uma vez.
    - datetime.datetime: gera o instante usado no mock de created_at.
    - sqlalchemy.select: monta a query de leitura do usuário salvo.
    - server.database.models.User: modelo/tabela de usuários testado aqui.

Fixtures usadas (definidas em conftest.py):
    - session: Session ligada a um SQLite em memória, com as tabelas criadas
      e derrubadas a cada teste.
    - return_mock: context manager que fixa o valor de created_at.

Classes:
    Não há classes definidas neste arquivo.

Funções:
    - test_create_user(session, return_mock): dentro do mock de tempo, cria
      um User, persiste com session.add() + session.commit(), recupera com
      session.scalar(select(User).where(...)) e compara asdict(user) com o
      dicionário esperado (user_id=1 e created_at=time_mock inclusos).
==========================================================================
"""
