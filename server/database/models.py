from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, registry

table_registry = registry()


@table_registry.mapped_as_dataclass
class User:
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(init=False, primary_key=True)
    user_email: Mapped[str] = mapped_column(unique=True)
    user_name: Mapped[str]
    user_password: Mapped[str]
    is_ativo: Mapped[bool]
    is_admin: Mapped[bool]
    user_time: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Define os MODELOS (ORM) da aplicação, ou seja, a representação em Python
    das TABELAS do banco de dados. Cada classe mapeada corresponde a uma
    tabela e cada atributo `Mapped[...]` a uma coluna. É a fonte única da
    verdade sobre a estrutura dos dados persistidos pela API.

Imports:
    - datetime.datetime: tipo da coluna created_at.
    - sqlalchemy.func: funções SQL (func.now() para default no servidor).
    - sqlalchemy.orm.Mapped, mapped_column, registry: API declarativa do
      SQLAlchemy para mapear classes/atributos em tabelas/colunas.

Classes:
    - User: mapeada para a tabela 'users'. Colunas: user_id (PK,
      autogerado), user_email (único), user_name, user_password, is_ativo,
      is_admin, user_time e created_at (default = data/hora do servidor).

Objetos:
    - table_registry: registry do SQLAlchemy usado para mapear as classes
      como dataclasses (@table_registry.mapped_as_dataclass).
==========================================================================
"""
