from dataclasses import asdict
from datetime import datetime

from sqlalchemy import select

from server.database.models import User


def test_create_user(session, return_mock):
    with return_mock(model=User, time=datetime.now()) as time_mock:
        user = User(
            user_email='teste@teste.com',
            user_name='teste',
            user_password='teste',
            is_ativo=True,
            is_admin=True,
            user_time='Teste',
        )

        session.add(user)
        session.commit()

        user = session.scalar(select(User).where(User.user_name == 'teste'))

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
    Testes unitários da camada de dados (ORM). Validam a criação de
    instâncias dos modelos do SQLAlchemy diretamente, sem passar pela API.

Imports:
    - server.database.models.User: modelo/tabela de usuários testado aqui.

Classes:
    Não há classes definidas neste arquivo.

Funções:
    - test_create_user(): instancia um User com os campos obrigatórios e
      garante que os atributos foram atribuídos corretamente
      (ex.: user.user_name == 'teste').
==========================================================================
"""
