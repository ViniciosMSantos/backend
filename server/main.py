from fastapi import FastAPI

from server.routes.auth_routes import auth_router

"""
### Comando para rodar api
## uvicorn main:app --reload
"""

app = FastAPI()

app.include_router(auth_router)


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Ponto de entrada da API. Cria a instância principal do FastAPI e
    registra os routers da aplicação. É este `app` que o uvicorn executa
    (server.main:app).

Imports:
    - fastapi.FastAPI: classe que cria a aplicação/servidor da API.
    - server.routes.auth_routes.auth_router: router com as rotas de
      autenticação, incluído no app.

Classes:
    Não há classes definidas neste arquivo.

Funções:
    Não há funções definidas neste arquivo.
    - app = FastAPI(): instância principal da API.
    - app.include_router(auth_router): acopla as rotas de autenticação.
==========================================================================
"""
