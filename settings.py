from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Utilidade:
    Centraliza a configuração da aplicação seguindo o padrão 12-factor: as
    variáveis sensíveis (como a URL do banco) ficam no arquivo `.env` — que
    NÃO é versionado — e são carregadas e validadas aqui. Assim o código
    nunca contém segredos e é possível trocar de ambiente (dev, teste,
    produção) apenas trocando o `.env`.
    """

    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8'
    )

    DATABASE_URL: str


"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Centraliza a configuração da API. Lê e VALIDA as variáveis de ambiente
    do arquivo `.env` (não versionado) na inicialização, seguindo o padrão
    12-factor. É quem fornece a DATABASE_URL usada por
    server/database/db.py para criar a engine, e também pelo Alembic nas
    migrations — assim a URL do banco fica em um lugar só.

Imports:
    - pydantic_settings.BaseSettings: classe base que lê variáveis de
      ambiente / arquivo .env e as valida com os tipos declarados.
    - pydantic_settings.SettingsConfigDict: configura de onde ler as
      variáveis (nome do arquivo e encoding).

Classes:
    - Settings: agrupa as configurações da API.
        * model_config: aponta para o arquivo '.env' com encoding utf-8.
        * DATABASE_URL (str): URL de conexão com o banco. Como não possui
          valor padrão, é OBRIGATÓRIA — se estiver ausente no .env, o
          Pydantic levanta um erro de validação já na inicialização.

Funções:
    Não há funções definidas neste arquivo.

Uso previsto:
    from settings import Settings
    engine = create_engine(Settings().DATABASE_URL)
==========================================================================
"""
