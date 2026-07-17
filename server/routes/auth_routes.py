from http import HTTPStatus

from fastapi import APIRouter

from server.database.schemas import UserPublic, UserSchema

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
async def create_user(usuario_schema: UserSchema):

    return usuario_schema


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Define as rotas de autenticação da API sob o prefixo '/auth'. Reúne os
    endpoints relacionados a usuários/autenticação em um APIRouter que é
    incluído no app principal (server/main.py).

Imports:
    - http.HTTPStatus: códigos de status HTTP padronizados (OK, CREATED).
    - fastapi.APIRouter: agrupa rotas em um módulo reutilizável.
    - server.database.schemas.UserPublic, UserSchema: schemas Pydantic de
      entrada (UserSchema) e de resposta pública (UserPublic).

Classes:
    Não há classes definidas neste arquivo.

Funções:
    - home(): rota GET '/auth/'. Retorna uma mensagem de teste. Status 200.
    - create_user(usuario_schema: UserSchema): rota POST
      '/auth/create_users'. Recebe os dados do usuário validados por
      UserSchema e retorna UserPublic (sem a senha). Status 201.

Objetos:
    - auth_router: APIRouter com prefix='/auth' e tag 'Autenticação'.
    - database: lista em memória usada temporariamente como armazenamento.
==========================================================================
"""
