from contextlib import contextmanager
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from server.database.db import get_session
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
def client(session):
    """
    POR QUE ESTA FIXTURE EXISTE:
    Testar rota HTTP sem precisar subir o uvicorn. O TestClient fala
    direto com o objeto `app` (em memória), então o teste é rápido e
    não depende de porta livre nem de servidor rodando.
    Como fixture, qualquer teste que declare `client` no parâmetro
    recebe uma instância nova e isolada automaticamente.

    POR QUE RECEBE `session`:
    Sem isso as rotas usariam o `get_session` real, ou seja o banco de
    DESENVOLVIMENTO — o teste sujaria dados de verdade. Declarar
    `session` como parâmetro faz o pytest montar o SQLite em memória
    antes deste client existir.

    `app.dependency_overrides[get_session]` é o mecanismo oficial do
    FastAPI para substituir uma dependência nos testes: onde a rota
    pedir `Depends(get_session)`, ela recebe a Session de teste. Repare
    que o override devolve a Session direto (`return`), sem `yield` —
    quem cuida de fechá-la é a fixture `session`.

    O `.clear()` no fim é obrigatório: dependency_overrides vive no
    objeto `app`, que é global. Sem limpar, o override vazaria para os
    testes seguintes.
    """

    def get_session_override():
        return session

    with TestClient(app) as client:
        app.dependency_overrides[get_session] = get_session_override

        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def session():
    """
    POR QUE ESTA FIXTURE EXISTE:
    Dar aos testes um banco DE VERDADE (o ORM roda SQL real), mas
    descartável — assim testamos a camada de dados sem sujar o banco
    de desenvolvimento.

    'sqlite:///:memory:' = banco que só existe na RAM; morre junto com
    o processo. Zero arquivo criado no disco.

    OS DOIS ARGUMENTOS EXTRAS existem por causa do TestClient:
    - poolclass=StaticPool: força o pool a reusar SEMPRE a MESMA
      conexão. Cada conexão nova para ':memory:' abriria um banco novo
      e VAZIO — as tabelas criadas aqui simplesmente não existiriam
      para a rota, e o teste falharia com 'no such table: users'.
    - check_same_thread=False: o SQLite, por padrão, proíbe usar a
      conexão fora da thread que a criou. O TestClient roda o app em
      outra thread, então sem isso o INSERT feito pela rota estouraria.
    """
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )

    # Cria as tabelas a partir dos modelos declarados no table_registry.
    # Sem isso o banco em memória estaria vazio e todo INSERT falharia.
    table_registry.metadata.create_all(engine)

    # `yield` no lugar de `return`: tudo antes é setup, tudo depois é
    # teardown. O teste roda "dentro" do yield e recebe esta Session.
    with Session(engine) as session:
        yield session

    # Teardown: derruba as tabelas ao fim de CADA teste. Garante
    # isolamento — um teste nunca enxerga os dados que outro criou
    # (por isso podemos afirmar user_id == 1 nos testes).
    table_registry.metadata.drop_all(engine)


@contextmanager
def _db_time_fake(*, model, time=datetime(2026, 7, 17)):
    """
    POR QUE ESTA FUNÇÃO EXISTE:
    A coluna `created_at` é preenchida pelo banco/ORM no momento do
    INSERT. Isso é NÃO determinístico: o teste nunca sabe o horário
    exato gravado, então não conseguiria comparar o registro inteiro.
    Aqui congelamos esse valor para o assert ficar previsível.

    Callback com a assinatura que o SQLAlchemy exige para eventos de
    mapper. `target` é a própria instância que está sendo inserida.
    """

    def fake_time(mapper, connection, target):
        # hasattr protege modelos que não tenham a coluna created_at.
        if hasattr(target, 'created_at'):
            target.created_at = time

    # Liga o callback ao evento 'before_insert': roda logo antes do
    # INSERT, sobrescrevendo o created_at que o modelo geraria.
    event.listen(model, 'before_insert', fake_time)

    # Entrega o horário fixo para o teste usar no assert
    # (`with return_mock(...) as time_mock`).
    yield time

    # Remove o listener ao sair do `with`. Sem isso o mock vazaria para
    # os testes seguintes, já que o evento é registrado na CLASSE do
    # modelo (estado global), não na sessão.
    event.remove(model, 'before_insert', fake_time)


@pytest.fixture
def return_mock():
    """
    POR QUE ESTA FIXTURE EXISTE:
    Um context manager não pode ser usado direto como fixture (o
    pytest executaria o `with` por conta própria). Então retornamos a
    FUNÇÃO em si — repare que não há parênteses em `_db_time_fake` —
    deixando o teste decidir quando abrir/fechar o mock e com quais
    argumentos (model e time).
    """
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
    - server.database.db.get_session: a dependência REAL de banco, usada
      aqui como CHAVE do dependency_overrides para ser substituída pela
      Session de teste.
    - server.database.models.table_registry: registry do ORM para criar as
      tabelas no banco de teste.
    - sqlalchemy.create_engine: cria a conexão (engine) com o banco
      (SQLite em memória para testes).
    - sqlalchemy.event: registra/remove listeners de eventos do ORM
      (usado para forçar o created_at no 'before_insert').
    - sqlalchemy.orm.Session: sessão do ORM entregue aos testes.
    - sqlalchemy.pool.StaticPool: pool que reusa uma única conexão —
      indispensável para o SQLite em memória sobreviver entre a fixture e
      as requisições feitas pelo TestClient.
    - contextlib.contextmanager: transforma _db_time_fake em um `with`.
    - datetime.datetime: valor padrão do created_at mockado.

Classes:
    Não há classes definidas neste arquivo.

Funções / Fixtures:
    - client(session) [fixture]: entrega um TestClient(app) já apontando
      para o banco de TESTE. Registra `app.dependency_overrides[
      get_session]` para que as rotas recebam a Session em memória em vez
      da do banco real, e limpa os overrides no teardown.
    - session() [fixture]: cria uma engine SQLite em memória (com
      StaticPool e check_same_thread=False), gera as tabelas a partir do
      metadata do ORM, entrega uma Session ao teste via yield e derruba as
      tabelas no teardown — garantindo isolamento total entre os testes.
    - _db_time_fake(model, time): context manager que registra um listener
      no evento 'before_insert' do SQLAlchemy para forçar a coluna
      `created_at` com um valor fixo (`time`), tornando os testes que
      dependem de data/hora determinísticos. Remove o listener ao sair.
    - return_mock() [fixture]: expõe o _db_time_fake para os testes usarem
      como `with return_mock(model=..., time=...) as time_mock:`.
==========================================================================
"""
