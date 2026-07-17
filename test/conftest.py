from contextlib import contextmanager
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from server.database.models import table_registry
from server.main import app

"""
O conftest.py é um arquivo especial do pytest usado para compartilhar
fixtures, hooks e configurações entre vários arquivos de teste, sem
precisar importá-los manualmente. O pytest o descobre automaticamente e
disponibiliza tudo o que está aqui para todos os testes do mesmo diretório
(e subdiretórios). Aqui, por exemplo, definimos a fixture `client` uma única
vez e a reutilizamos em qualquer teste que precise fazer requisições à API.
"""


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    table_registry.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

    table_registry.metadata.drop_all(engine)


@contextmanager
def _db_time_fake(*, model, time=datetime(2026, 7, 17)):
    def fake_time(mapper, connection, target):
        if hasattr(target, 'created_at'):
            target.created_at = time

    event.listen(model, 'before_insert', fake_time)
    yield time
    event.remove(model, 'before_insert', fake_time)


@pytest.fixture
def return_mock():
    return _db_time_fake


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Arquivo especial do pytest que centraliza fixtures e configurações
    compartilhadas por todos os testes do diretório (e subdiretórios). O
    pytest o descobre automaticamente, sem necessidade de import manual.

Imports:
    - pytest: framework de testes / decorador @pytest.fixture.
    - fastapi.testclient.TestClient: cliente HTTP para testar a API sem
      subir um servidor real.
    - server.main.app: instância da API usada pelo TestClient.
    - server.database.models.table_registry: registry do ORM para criar as
      tabelas no banco de teste.
    - sqlalchemy.create_engine: cria a conexão (engine) com o banco
      (SQLite em memória para testes).

Classes:
    Não há classes definidas neste arquivo.

Funções / Fixtures:
    - client() [fixture]: retorna um TestClient(app) reutilizável para fazer
      requisições à API nos testes.
    - session(): cria uma engine SQLite em memória e gera as tabelas a
      partir do metadata do ORM (base para futura fixture de banco).
    - _db_time_fake(model, time): context manager que registra um listener
      no evento 'before_insert' do SQLAlchemy para forçar a coluna
      `created_at` com um valor fixo (`time`), tornando os testes que
      dependem de data/hora determinísticos. Remove o listener ao sair.
    - return_mock() [fixture]: expõe o _db_time_fake para os testes usarem
      como `with return_mock(model=..., time=...) as time_mock:`.
==========================================================================
"""
