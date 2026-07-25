from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
import settings
from server.database.models import table_registry

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option('sqlalchemy.url', settings.Settings().DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = table_registry.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Script de configuração que o Alembic executa ANTES de qualquer comando
    (`alembic revision`, `upgrade`, `downgrade`, ...). É a ponte entre o
    Alembic e este projeto: define de onde vem a URL do banco e quais
    metadados dos modelos ele deve conhecer. Sem ele, o Alembic não saberia
    em qual banco mexer nem conseguiria fazer `--autogenerate`.

    Duas customizações foram feitas no arquivo gerado por `alembic init`:
      1) config.set_main_option('sqlalchemy.url', Settings().DATABASE_URL)
         -> usa a URL do .env em vez da do alembic.ini, mantendo segredos
            fora do versionamento;
      2) target_metadata = table_registry.metadata
         -> entrega o schema DESEJADO (models.py) para o Alembic comparar
            com o schema ATUAL do banco; é isso que habilita o
            `--autogenerate`.

    Guia de uso e comandos: migrations/GUIA-ALEMBIC.md

Imports:
    - logging.config.fileConfig: aplica a configuração de logging do
      alembic.ini (as linhas "INFO [alembic...]" na saída).
    - sqlalchemy.engine_from_config: cria a Engine a partir da seção
      [alembic] da config (prefixo 'sqlalchemy.').
    - sqlalchemy.pool: fornece NullPool — migração não precisa de pool de
      conexões.
    - alembic.context: objeto que expõe a config e executa as migrações.
    - settings: módulo do projeto com a classe Settings (lê o .env). Só é
      importável por causa do `prepend_sys_path = .` no alembic.ini.
    - server.database.models.table_registry: registry do SQLAlchemy de onde
      sai o metadata das tabelas.

Classes:
    Não há classes definidas neste arquivo.

Funções:
    - run_migrations_offline(): modo offline. Configura o contexto apenas
      com a URL (sem abrir conexão) e EMITE O SQL em vez de executá-lo.
      É o caminho usado pela flag `--sql`. Não retorna valor.
    - run_migrations_online(): modo padrão. Cria a Engine, abre uma conexão
      real e roda as migrações dentro de uma transação. Não retorna valor.

Objetos:
    - config: objeto de configuração do Alembic (lido do alembic.ini e
      sobrescrito aqui com a DATABASE_URL).
    - target_metadata: metadata das tabelas mapeadas, usado pelo
      autogenerate para calcular o diff schema desejado x schema atual.
==========================================================================
"""
