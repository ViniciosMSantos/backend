from pydantic import BaseModel, EmailStr


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

    O Pydantic garante que apenas esses campos serão serializados e
    retornados na resposta, mantendo a senha protegida.
    """

    email: EmailStr
    nome: str
    is_ativo: bool
    is_admin: bool
    time: str


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Define os SCHEMAS (Pydantic) da API: os "contratos" que descrevem como
    os dados chegam nas requisições e como são retornados nas respostas.
    Garantem validação de campos/tipos e a serialização segura dos dados
    (ex.: não expor a senha nas respostas).

Imports:
    - pydantic.BaseModel: classe base que fornece validação e serialização.
    - pydantic.EmailStr: tipo que valida se o campo é um e-mail válido.

Classes:
    - UserSchema: schema de ENTRADA para criar usuário. Campos: email,
      nome, senha, is_ativo, is_admin, time (todos obrigatórios).
    - UserPublic: schema de SAÍDA (resposta pública). Igual ao UserSchema
      porém SEM o campo 'senha', protegendo a senha do usuário.

Funções:
    Não há funções definidas neste arquivo.
==========================================================================
"""
