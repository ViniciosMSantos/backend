from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from settings import Settings

engine = create_engine(Settings().DATABASE_URL)


def get_session():
    """
    Dependência do FastAPI que entrega uma Session do SQLAlchemy por
    requisição.

    O `with` garante que a conexão é devolvida ao pool no fim da
    requisição, mesmo se a rota levantar exceção. O `yield` (em vez de
    `return`) é o que transforma isso em uma dependência com teardown:
    tudo antes é setup, tudo depois roda quando a resposta já saiu.

    Nas rotas: `session=Depends(get_session)`.
    Nos testes: `app.dependency_overrides[get_session]` troca esta
    função por uma que devolve a Session do SQLite em memória.
    """
    with Session(engine) as session:
        yield session


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Ponto único de conexão com o banco de dados. Cria a `engine` (o pool de
    conexões, criado UMA vez quando o módulo é importado) e expõe a
    dependência `get_session`, que as rotas usam para conversar com o banco.
    Separar isso em um módulo próprio evita import circular entre rotas e
    modelos e é o que permite substituir o banco real por um de teste.

Imports:
    - sqlalchemy.create_engine: cria a engine/pool a partir da URL do banco.
    - sqlalchemy.orm.Session: sessão do ORM — a "conversa" com o banco, onde
      ficam os objetos pendentes até o commit.
    - settings.Settings: lê a DATABASE_URL do arquivo .env (padrão
      12-factor), para a URL do banco não ficar escrita no código.

Classes:
    Não há classes definidas neste arquivo.

Funções:
    - get_session(): generator usado como dependência do FastAPI
      (`Depends(get_session)`). Abre uma Session, entrega ao endpoint via
      yield e a fecha no fim da requisição.

Objetos:
    - engine: engine do SQLAlchemy apontando para Settings().DATABASE_URL.
      Compartilhada por toda a aplicação.
==========================================================================
"""
