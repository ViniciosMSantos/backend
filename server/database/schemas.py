from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserSchema(BaseModel):
    """
    Schema utilizado para validar os dados de um cliente.

    Todos os campos abaixo são obrigatórios e devem ser enviados
    na requisição para que a validação seja concluída com sucesso.

    Campos obrigatórios:
    - email (str): E-mail do cliente.
    - nome (str): Nome completo do cliente.
    - senha (str): Senha de acesso.
    - is_ativo (bool): Indica se o cliente está ativo.
    - is_admin (bool): Indica se o cliente possui privilégios de administrador.
    - time (str): Time ou equipe ao qual o cliente pertence.

    Caso algum campo esteja ausente ou com o tipo incorreto, o
    Pydantic retornará um erro de validação automaticamente.
    """

    email: EmailStr
    nome: str
    senha: str
    is_ativo: bool
    is_admin: bool
    time: str


class UserPublic(BaseModel):
    """
    Schema utilizado para retornar os dados públicos de um cliente.

    Diferente do `UserSchema`, este schema NÃO inclui o campo `senha`,
    pois ele é usado nas respostas da API. Assim, evitamos expor a senha
    do cliente para quem consome a API.

    Campos retornados:
    - email (str): E-mail do cliente.
    - nome (str): Nome completo do cliente.
    - is_ativo (bool): Indica se o cliente está ativo.
    - is_admin (bool): Indica se o cliente possui privilégios de administrador.
    - time (str): Time ou equipe ao qual o cliente pertence.
    - id (int): Identificador do cliente gerado pelo banco.

    O Pydantic garante que apenas esses campos serão serializados e
    retornados na resposta, mantendo a senha protegida.

    Como o modelo ORM (`User`) usa nomes com prefixo (`user_id`,
    `user_email`, `user_name`, `user_time`), cada um desses campos declara
    um `validation_alias` apontando para o nome da coluna. Junto com
    `from_attributes=True`, isso permite que o FastAPI leia o objeto do
    SQLAlchemy diretamente. As chaves do JSON de resposta continuam sendo
    `email`, `nome`, `time` e `id`.

    ⚠️ ERRO FÁCIL DE COMETER: esquecer o alias em um dos campos. Declarar
    `id: int` sem `validation_alias='user_id'` faz o Pydantic procurar o
    atributo `id` no objeto User — que não existe, a coluna é `user_id` —
    e o FastAPI responde 500 com
    `ResponseValidationError: ('response', 'id') Field required`.
    """

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

    id: int = Field(validation_alias='user_id')
    email: EmailStr = Field(validation_alias='user_email')
    nome: str = Field(validation_alias='user_name')
    is_ativo: bool
    is_admin: bool
    time: str = Field(validation_alias='user_time')


class UserList(BaseModel):
    """
    Schema utilizado para retornar uma LISTA de usuários.

    Precisa herdar de `BaseModel`: o FastAPI só aceita tipos Pydantic
    válidos em `response_model`. Uma classe comum (sem BaseModel) gera
    `FastAPIError: Invalid args for response field!`.

    Campos retornados:
    - users (list[UserPublic]): lista de usuários já no formato público
      (sem a senha).

    O envelope `{'users': [...]}` deixa a resposta extensível — mais
    tarde é possível somar campos como total/página sem quebrar o
    contrato de quem consome a API.
    """

    users: list[UserPublic]


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Define os SCHEMAS (Pydantic) da API: os "contratos" que descrevem como
    os dados chegam nas requisições e como são retornados nas respostas.
    Garantem validação de campos/tipos e a serialização segura dos dados
    (ex.: não expor a senha nas respostas).

Imports:
    - pydantic.BaseModel: classe base que fornece validação e serialização.
    - pydantic.ConfigDict: configura o schema (from_attributes para ler
      objetos do ORM; validate_by_name para aceitar também o nome do campo).
    - pydantic.EmailStr: tipo que valida se o campo é um e-mail válido.
    - pydantic.Field: usado para declarar o validation_alias que liga o
      campo do schema à coluna correspondente do modelo ORM.

Classes:
    - UserSchema: schema de ENTRADA para criar usuário. Campos: email,
      nome, senha, is_ativo, is_admin, time (todos obrigatórios).
    - UserPublic: schema de SAÍDA (resposta pública). Igual ao UserSchema
      porém SEM o campo 'senha' e COM o 'id', protegendo a senha do
      usuário. Lê o objeto User do SQLAlchemy via from_attributes,
      traduzindo user_email -> email, user_name -> nome, user_time -> time
      e user_id -> id.
    - UserList: schema de SAÍDA da listagem. Envelopa vários UserPublic em
      {'users': [...]}. Herda de BaseModel para poder ser usado como
      response_model.

Funções:
    Não há funções definidas neste arquivo.
==========================================================================
"""
