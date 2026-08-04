from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from server.database.db import get_session
from server.database.models import User
from server.database.schemas import UserList, UserPublic, UserSchema

auth_router = APIRouter(prefix='/auth', tags=['Autenticação'])

database = []


@auth_router.get('/', status_code=HTTPStatus.OK)
async def home():
    """
    Esta é a rota padrão de autenticação no sistema.
    """
    return {'mensagem': 'Olá mundo!'}


@auth_router.post(
    '/create_users', status_code=HTTPStatus.CREATED, response_model=UserPublic
)
async def create_user(
    usuario_schema: UserSchema, session=Depends(get_session)
):

    db_user = session.scalar(
        select(User).where(User.user_email == usuario_schema.email)
    )

    if db_user:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail='E-mail já cadastrado.'
        )

    db_user = User(
        user_email=usuario_schema.email,
        user_password=usuario_schema.senha,
        user_time=usuario_schema.time,
        user_name=usuario_schema.nome,
        is_ativo=usuario_schema.is_ativo,
        is_admin=usuario_schema.is_admin,
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


@auth_router.get('/users', status_code=HTTPStatus.OK, response_model=UserList)
def read_users(limit: int = 10, offset: int = 1, session=Depends(get_session)):
    users = session.scalars(select(User).limit(limit).offset(offset)).all()
    return {'users': users}


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Define as rotas de autenticação da API sob o prefixo '/auth'. Reúne os
    endpoints relacionados a usuários/autenticação em um APIRouter que é
    incluído no app principal (server/main.py).

Imports:
    - http.HTTPStatus: códigos de status HTTP padronizados (OK, CREATED,
      CONFLICT).
    - fastapi.APIRouter: agrupa rotas em um módulo reutilizável.
    - fastapi.Depends: injeta dependências no endpoint — aqui, a Session do
      banco. É o que permite aos testes trocarem o banco real pelo de
      teste via `app.dependency_overrides`.
    - fastapi.HTTPException: exceção que o FastAPI converte em resposta de
      erro HTTP (é a do FastAPI; não existe `HTTPException` em `http`).
    - sqlalchemy.select: monta as queries de busca/listagem de usuários.
    - server.database.db.get_session: dependência que abre/fecha a Session
      do SQLAlchemy por requisição.
    - server.database.models.User: modelo ORM da tabela de usuários.
    - server.database.schemas.UserList, UserPublic, UserSchema: schemas
      Pydantic de entrada (UserSchema), de resposta pública (UserPublic) e
      de listagem (UserList).

Classes:
    Não há classes definidas neste arquivo.

Funções:
    - home(): rota GET '/auth/'. Retorna uma mensagem de teste. Status 200.
    - create_user(usuario_schema: UserSchema, session): rota POST
      '/auth/create_users'. Verifica se já existe usuário com o mesmo
      e-mail (409 CONFLICT em caso positivo), grava o novo usuário no banco
      com add() + commit() + refresh() e retorna UserPublic (sem a senha).
      Status 201.
        * O `refresh(db_user)` é necessário para o objeto voltar do banco
          com as colunas geradas por ele (user_id e created_at) — sem isso
          o `id` da resposta viria vazio.
    - read_users(limit, offset, session): rota GET '/auth/users'. Lista os
      usuários paginados com session.scalars(select(User).limit().offset())
      e retorna UserList, ou seja {'users': [...]} com cada usuário no
      formato público. Status 200.
        * limit (int, padrão 10): quantos registros retornar.
        * offset (int, padrão 1): quantos registros pular. ⚠️ O padrão
          deveria ser 0 — com 1 a primeira página pula o primeiro usuário.

Objetos:
    - auth_router: APIRouter com prefix='/auth' e tag 'Autenticação'.
    - database: lista em memória que servia de "banco" antes do SQLAlchemy.
      Hoje está SEM USO — as rotas persistem no banco de verdade. Mantida
      apenas como registro da evolução do projeto; pode ser removida.

Detalhe aprendido aqui:
    A validação do `response_model` acontece DEPOIS do commit. Se o schema
    de resposta não conseguir ler algum campo do objeto ORM, o registro é
    gravado no banco e o cliente recebe 500 (ResponseValidationError) —
    foi o que aconteceu quando `UserPublic.id` estava sem o
    validation_alias='user_id'.
==========================================================================
"""
