# Resumo de Estudos — API com FastAPI

> Material de estudo consolidando **tudo** o que foi construído neste projeto até
> agora. A espinha dorsal é o **passo a passo** da seção 2, que reconstrói o
> projeto na ordem em que cada peça nasceu; em volta dele vêm a visão geral, os
> diagramas de arquitetura e de fluxo, o detalhe arquivo por arquivo e o roteiro
> do que vem a seguir.

---

## 1. Visão geral

Uma API de **autenticação/usuários** construída com o *stack* Python moderno,
com foco em **aprender o ecossistema completo** (não só o FastAPI):

| Camada | Ferramenta | Papel |
|--------|-----------|-------|
| Framework web | **FastAPI** | Cria a API, rotas e documentação automática |
| Servidor ASGI | **uvicorn** | Sobe e executa a aplicação |
| Validação / contratos | **Pydantic** | Valida entrada e serializa saída (schemas) |
| Persistência (ORM) | **SQLAlchemy 2.0** | Mapeia classes Python ↔ tabelas do banco |
| Migrations | **Alembic** | Versiona o *schema* do banco (upgrade/downgrade) |
| Inspeção do banco | **harlequin** (via `uvx`) | Cliente SQL no terminal para conferir o banco |
| Configuração | **pydantic-settings** | Lê variáveis de ambiente do `.env` |
| Gerenciador de projeto | **uv** | Python, venv e dependências |
| Automação de tarefas | **taskipy** | Atalhos `task run/lint/test/format` |
| Lint + Format | **ruff** | Qualidade e padronização de código |
| Testes | **pytest** + **pytest-cov** | Testes e cobertura |
| Cliente de teste | **httpx** / TestClient | Testa a API sem subir servidor real |

Requisitos: **Python >= 3.13**.

### Estágio atual do projeto

Os blocos já existem e o **banco real já foi criado**, mas a rota **ainda não
está ligada a ele**:

| Bloco | Situação |
|-------|----------|
| Rotas + schemas (`/auth`) | ✅ funcionando (valida entrada, devolve saída) |
| Modelo ORM (`User`) | ✅ definido e **testado**, mas só nos testes |
| Configuração (`Settings`) | ✅ lê o `.env`, mas **nenhum `create_engine` usa** ela |
| Migrations (Alembic) | ✅ tabela `users` criada no `database.db` (revisão `3561799945aa`) |
| Sessão na rota | ⏳ falta o `get_session` + `Depends` |

Ou seja: o **schema** do banco real já existe (foi o Alembic que o criou), mas a
API **ainda não grava** nele — `create_user` só valida e devolve. O único lugar
onde o SQLAlchemy realmente persiste dados hoje é a fixture `session` dos testes
(SQLite em memória). Fechar esse elo é o próximo passo do estudo (ver seção 10).

---

## 2. Passo a passo — como este projeto foi construído

Em vez de um mapa espalhado, aqui está a **ordem** em que as peças nascem. Cada
passo só faz sentido depois do anterior, e cada um responde a uma pergunta:
*"que problema apareceu agora?"*.

```mermaid
graph LR
    P1["1<br/>Ambiente<br/>uv + task"] --> P2["2<br/>App<br/>main.py"]
    P2 --> P3["3<br/>Rotas<br/>auth_routes.py"]
    P3 --> P4["4<br/>Entrada<br/>UserSchema"]
    P4 --> P5["5<br/>Saída<br/>UserPublic"]
    P5 --> P6["6<br/>Tabela<br/>models.py"]
    P6 --> P7["7<br/>Config<br/>settings.py"]
    P7 --> P8["8<br/>Testes<br/>conftest + test_*"]
    P8 --> P9["9<br/>Migrations<br/>Alembic"]
    P9 --> P10["10<br/>Ligar rota<br/>ao banco ⏳"]
```

---

### Passo 1 — Preparar o terreno (ambiente e atalhos)

**Problema:** antes de escrever qualquer rota, preciso de um Python isolado,
dependências travadas e comandos iguais para todo mundo.

**O que foi feito:** `uv` cria a venv e instala as deps (`pyproject.toml` +
`uv.lock`); `taskipy` transforma comandos longos em `task run`, `task lint`,
`task format`, `task test`; `ruff` padroniza o estilo (`line-length = 79`,
aspas simples).

**Como sei que deu certo:** `task lint` roda e não acusa nada.

---

### Passo 2 — Criar a aplicação (o objeto que o servidor executa)

**Problema:** o uvicorn precisa de **um** objeto para servir.

**Arquivo:** [server/main.py](../server/main.py)

```python
app = FastAPI()
app.include_router(auth_router)
```

**Lógica:** `main.py` não tem regra de negócio — ele só **monta**. Cada grupo de
rotas vira um router e é plugado aqui. É o "quadro de tomadas" da API.

**Como sei que deu certo:** `task run` sobe e `http://127.0.0.1:8000/docs` abre.

---

### Passo 3 — Criar as rotas (traduzir URL em função Python)

**Problema:** preciso dizer *qual método + qual caminho* chama *qual função*.

**Arquivo:** [server/routes/auth_routes.py](../server/routes/auth_routes.py)

```python
auth_router = APIRouter(prefix='/auth', tags=['Autenticação'])

@auth_router.get('/', status_code=HTTPStatus.OK)
async def home(): ...
```

**Lógica:** o `prefix='/auth'` evita repetir o caminho em cada rota e a `tag`
agrupa os endpoints no `/docs`. O `status_code` é **declarado**, não improvisado:
`200` para leitura, `201` para criação.

**Como sei que deu certo:** `GET /auth/` devolve `{'mensagem': 'Olá mundo!'}`.

---

### Passo 4 — Validar o que ENTRA (`UserSchema`)

**Problema:** o cliente pode mandar qualquer JSON. Não quero checar campo por
campo dentro da função.

**Arquivo:** [server/database/schemas.py](../server/database/schemas.py)

```python
class UserSchema(BaseModel):
    email: EmailStr
    nome: str
    senha: str
    ...
```

**Lógica:** ao anotar o parâmetro da rota com `usuario_schema: UserSchema`, o
FastAPI valida **antes** de executar a função. JSON errado nunca chega no corpo
da rota — vira **422** automaticamente. O `EmailStr` já cuida do formato do
e-mail.

**Como sei que deu certo:** mandar um payload sem `senha` retorna 422.

---

### Passo 5 — Controlar o que SAI (`UserPublic`)

**Problema:** a senha chegou na entrada, mas **não pode voltar** na resposta.

```python
@auth_router.post(
    '/create_users', status_code=HTTPStatus.CREATED, response_model=UserPublic
)
async def create_user(usuario_schema: UserSchema):
    return usuario_schema
```

**Lógica:** `UserPublic` é o `UserSchema` **sem `senha`**. Mesmo a função
devolvendo o objeto completo, o `response_model` faz o FastAPI serializar
**apenas** os campos declarados. A proteção não depende de eu lembrar de remover
a senha — está no contrato.

**Como sei que deu certo:** o 201 volta sem o campo `senha`.

---

### Passo 6 — Descrever a tabela (`models.py`)

**Problema:** validar e devolver não guarda nada. Ao reiniciar, tudo se perde.

**Arquivo:** [server/database/models.py](../server/database/models.py)

```python
@table_registry.mapped_as_dataclass
class User:
    __tablename__ = 'users'
    user_id: Mapped[int] = mapped_column(init=False, primary_key=True)
    user_email: Mapped[str] = mapped_column(unique=True)
```

**Lógica:** classe = tabela, atributo `Mapped` = coluna. `init=False` significa
"não entra no construtor, **o banco preenche**" (PK e `created_at`).
`unique=True` impede e-mail repetido no nível do banco. O `table_registry`
guarda o *metadata* usado depois por `create_all`.

**⚠️ Não confundir:** *schema* (Pydantic) fala com o **cliente**; *model*
(SQLAlchemy) fala com o **banco**. Por isso vivem em arquivos separados — e por
isso a rota, no futuro, vai **converter** um no outro.

---

### Passo 7 — Tirar o segredo do código (`settings.py`)

**Problema:** a URL do banco muda entre dev, teste e produção — e tem senha
dentro.

**Arquivo:** [settings.py](../settings.py)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', ...)
    DATABASE_URL: str
```

**Lógica:** `DATABASE_URL` **sem valor padrão** = obrigatória. Se faltar no
`.env`, o Pydantic quebra já na inicialização (erro claro, cedo) em vez de falhar
na primeira query. O `.env` está no `.gitignore`; trocar de ambiente é trocar o
arquivo, não o código.

---

### Passo 8 — Provar que funciona (testes)

**Problema:** como saber que uma mudança não quebrou o que já existia?

**Arquivos:** [test/conftest.py](../test/conftest.py),
[test/test_app.py](../test/test_app.py), [test/test_db.py](../test/test_db.py)

1. **`client`** → `TestClient(app)` chama as rotas **sem subir servidor**.
2. **`session`** → engine **SQLite em memória**, `create_all` antes e `drop_all`
   depois: cada teste começa com banco limpo.
3. **`return_mock`** → listener no evento `before_insert` congela o `created_at`,
   deixando o teste de data/hora determinístico.
4. Os testes seguem **AAA** (Arrange, Act, Assert): `test_app.py` valida o
   contrato HTTP, `test_db.py` valida o ORM.

**Como sei que deu certo:** `task test` passa e o `--cov=server` mostra a
cobertura.

---

### Passo 9 — Criar o banco de verdade (Alembic)

**Problema:** `models.py` descreve a tabela, mas **descrever não é criar**. E
mesmo criando com `create_all`, na próxima vez que eu adicionar uma coluna ele
não sabe **alterar** a tabela existente — só criar o que não existe. Sem uma
ferramenta de migração, cada mudança de modelo significaria apagar e recriar o
banco, perdendo os dados.

**O que foi feito:**

```bash
uv add alembic
uv run alembic init migrations             # cria migrations/ + alembic.ini
# ajustes no migrations/env.py (ver abaixo)
uv run alembic revision --autogenerate -m "create users table"
uv run alembic upgrade head                # criou users em database.db
```

**Arquivos:** [alembic.ini](../alembic.ini), [migrations/env.py](../migrations/env.py),
[migrations/versions/3561799945aa_create_users_table.py](../migrations/versions/3561799945aa_create_users_table.py)

Duas linhas no `env.py` são o que liga o Alembic a **este** projeto:

```python
# usa a URL do .env em vez da do alembic.ini (segredo fora do versionamento)
config.set_main_option('sqlalchemy.url', settings.Settings().DATABASE_URL)

# diz quais tabelas o Alembic conhece -> é isso que habilita o --autogenerate
target_metadata = table_registry.metadata
```

**Lógica:** o Alembic é o **Git do schema**. Cada mudança vira um arquivo em
`migrations/versions/` com `upgrade()` (aplica) e `downgrade()` (desfaz), e cada
um aponta para o anterior via `down_revision`, formando uma corrente. O Alembic
grava na tabela `alembic_version`, **dentro do próprio banco**, em qual revisão
aquele banco está — é assim que ele sabe o que falta aplicar. Com o
`target_metadata` apontando para o `table_registry`, o `--autogenerate` compara o
*desejado* (models.py) com o *atual* (banco) e escreve o diff sozinho.

**Como sei que deu certo:**

```bash
uv run alembic current        # -> 3561799945aa (head)
uvx harlequin database.db     # SELECT * FROM users; e SELECT * FROM alembic_version;
```

> ⚠️ Note que os **testes não usam Alembic** — a fixture `session` continua
> usando `create_all` em SQLite em memória, porque lá o objetivo é testar o ORM
> rápido e isolado. Consequência: teste passando **não prova** que a migration
> está correta; quem prova é rodar `upgrade`/`downgrade` no banco real.

**Guia completo** de comandos, armadilhas e do `uvx harlequin`:
[migrations/GUIA-ALEMBIC.md](../migrations/GUIA-ALEMBIC.md).

---

### Passo 10 — O passo que ainda falta: ligar a rota ao banco ⏳

Hoje os passos 6 e 7 existem **isolados**: o `User` só é usado nos testes e
nenhum `create_engine` lê o `Settings` (o único que lê é o `env.py` do Alembic).
A tabela já existe no `database.db` — falta a API escrever nela. Fechar o ciclo é:

1. criar o módulo de conexão: `create_engine(Settings().DATABASE_URL)` +
   `get_session()`;
2. injetar na rota: `session: Session = Depends(get_session)`;
3. converter `UserSchema` → `User`, `session.add()` + `commit()`;
4. apagar a lista `database = []` (declarada e não usada);
5. nos testes, `app.dependency_overrides[get_session]` para reaproveitar o
   SQLite em memória.

Detalhes e o que vem depois disso na [seção 10](#10-próximos-passos-sugeridos).

### Resumo dos passos em forma de tabela

| # | Peça | Pergunta que ela responde | Lógica em uma frase |
|---|------|---------------------------|---------------------|
| 1 | `pyproject.toml` | *Como o time roda o projeto igual?* | Deps travadas, regras de lint e atalhos `task` para todo mundo usar o mesmo comando. |
| 2 | `main.py` | *Onde a aplicação começa?* | Um único objeto `app` que o servidor executa e no qual todos os routers são plugados. |
| 3 | `auth_routes.py` | *Qual URL faz o quê?* | Traduz método + caminho HTTP em uma função Python, com status code e `response_model` declarados. |
| 4 | `UserSchema` | *O que o cliente pode mandar?* | Filtro de entrada: se o JSON não bater com o tipo declarado, a função nem é chamada. |
| 5 | `UserPublic` | *O que o cliente pode ver?* | Filtro de saída: o FastAPI serializa só os campos declarados, então a senha nunca vaza. |
| 6 | `models.py` | *Como o dado fica guardado?* | Classe Python = tabela; atributo `Mapped` = coluna; o SQLAlchemy gera o SQL. |
| 7 | `settings.py` | *O que muda entre dev, teste e produção?* | Tudo o que é ambiente/segredo sai do código e vira variável validada pelo Pydantic. |
| 8 | `conftest.py` | *Como testar sem depender do mundo real?* | Fixtures montam um cenário isolado — servidor falso, banco em memória e relógio congelado. |
| 9 | `migrations/` | *Como o schema evolui sem perder dados?* | Cada mudança de tabela vira um arquivo versionado com `upgrade()`/`downgrade()`; o banco guarda em que revisão está. |
| 10 | *(a fazer)* | *Como o dado sobrevive ao restart?* | `Depends(get_session)` na rota + `session.add/commit` — o elo que fecha o ciclo. |

---

## 3. Mapa da arquitetura

```mermaid
graph TD
    subgraph Cliente
        C[HTTP Client / Browser / TestClient]
    end

    subgraph "Aplicação FastAPI"
        M["server/main.py<br/>app = FastAPI()"]
        R["server/routes/auth_routes.py<br/>APIRouter (prefix /auth)"]
        S["server/database/schemas.py<br/>Pydantic: UserSchema / UserPublic"]
        MO["server/database/models.py<br/>SQLAlchemy: User"]
        CFG["settings.py<br/>Settings (.env)"]
    end

    subgraph "Migrations"
        AL["migrations/env.py<br/>Alembic"]
        VER["migrations/versions/<br/>3561799945aa"]
    end

    subgraph "Persistência"
        DB[("database.db<br/>via DATABASE_URL")]
        TDB[("SQLite :memory:<br/>só nos testes")]
    end

    C -->|requisição| M
    M -->|include_router| R
    R -->|valida entrada| S
    R -->|resposta UserPublic| C
    R -.->|FALTA: injetar session| MO
    MO -->|hoje só é usado por| TDB
    MO -->|metadata comparado por| AL
    CFG -->|DATABASE_URL| AL
    AL --> VER
    VER -->|upgrade cria a tabela| DB
    CFG -.->|FALTA: create_engine| DB
```

> As setas **tracejadas** são o que ainda não existe no código. A rota
> `create_user` apenas valida com `UserSchema` e devolve `UserPublic`;
> `models.py` e `settings.py` estão prontos, mas quem os usa de verdade hoje é o
> **Alembic** (que já criou a tabela `users` no `database.db`) — não a aplicação.

---

## 4. Fluxo de uma requisição (criar usuário)

```mermaid
sequenceDiagram
    participant Cli as Cliente
    participant App as FastAPI (main)
    participant Rt as auth_router
    participant In as UserSchema (Pydantic)
    participant Out as UserPublic (Pydantic)

    Cli->>App: POST /auth/create_users (JSON)
    App->>Rt: roteia para create_user()
    Rt->>In: valida campos e tipos
    alt dados inválidos
        In-->>Cli: 422 Unprocessable Entity
    else dados válidos
        In->>Rt: objeto validado
        Rt->>Out: response_model remove a senha
        Out-->>Cli: 201 CREATED (sem senha)
    end
```

O ponto-chave: **entra `UserSchema` (com senha), sai `UserPublic` (sem senha)**.
O `response_model=UserPublic` garante que a senha nunca vaza na resposta —
mesmo que a função `create_user` devolva o objeto completo, o FastAPI serializa
usando **apenas** os campos declarados em `UserPublic`.

---

## 5. Estrutura de pastas

```
fastapi_1/
├── server/                     # código da aplicação
│   ├── main.py                 # ponto de entrada: cria app e inclui routers
│   ├── routes/
│   │   └── auth_routes.py       # rotas /auth (home, create_users)
│   └── database/
│       ├── models.py            # modelos ORM (tabela User)
│       └── schemas.py           # schemas Pydantic (entrada/saída)
├── test/                       # testes automatizados
│   ├── conftest.py             # fixtures compartilhadas (client, session, mock)
│   ├── test_app.py             # testes de integração (HTTP)
│   ├── test_db.py              # teste do ORM com banco em memória
│   └── users/
│       └── test_create_user.py  # reservado p/ testes de criação de usuário
├── migrations/                 # versionamento do SCHEMA do banco (Alembic)
│   ├── env.py                  # config executada pelo Alembic (URL + metadata)
│   ├── script.py.mako          # template de cada nova revisão
│   ├── versions/
│   │   └── 3561799945aa_create_users_table.py  # revisão: cria a tabela users
│   ├── README                  # arquivo padrão do `alembic init`
│   └── GUIA-ALEMBIC.md         # guia de estudo do Alembic (comandos, cuidados)
├── docs/                       # documentação de estudo
│   ├── comandos-uv-task-ruff.md # guia de uv, taskipy e ruff
│   └── resumo-estudos.md        # (este arquivo)
├── alembic.ini                 # config do Alembic (script_location, logging)
├── database.db                 # banco SQLite local (gerado; não versionar)
├── settings.py                 # configurações via .env (DATABASE_URL)
├── pyproject.toml              # dependências, ruff, pytest e tasks
├── uv.lock                     # versões travadas (reprodutibilidade)
├── .python-version             # versão do Python usada pelo uv
├── .gitignore                  # ignora .env, .venv, caches, coverage, database.db
├── CLAUDE.md                   # guia/regras do projeto
├── .env.example                # MODELO das variáveis (versionado)
└── .env                        # variáveis de ambiente (NÃO versionado)
```

> **Sobre versionamento:** o `.env` (segredos), o `database.db` (artefato local),
> os `__pycache__/` e o `.coverage` **não** vão para o Git — o schema do banco
> mora em `migrations/versions/`, não no arquivo `.db`. Já `alembic.ini`,
> `migrations/` e `.env.example` **devem** ser versionados: são eles que permitem
> a outra pessoa clonar o repo, criar o `.env` a partir do exemplo e chegar ao
> mesmo schema com um `alembic upgrade head`.
>
> ⚠️ Lembrete de estudo: adicionar algo ao `.gitignore` **não desrastreia** o que
> já foi commitado antes — para isso é preciso
> `git rm -r --cached <caminho>` (remove do índice, mantém o arquivo no disco).

---

## 6. Detalhe por arquivo

### `server/main.py` — ponto de entrada
- Cria a instância principal: `app = FastAPI()`.
- Acopla as rotas: `app.include_router(auth_router)`.
- É o que o uvicorn executa: `uvicorn server.main:app --reload`.

### `server/routes/auth_routes.py` — rotas de autenticação
- `auth_router = APIRouter(prefix='/auth', tags=['Autenticação'])` agrupa as rotas.
  O `prefix` evita repetir `/auth` em cada rota e a `tag` agrupa os endpoints
  na documentação automática (`/docs`).
- `GET /auth/` → `home()`: retorna `{'mensagem': 'Olá mundo!'}` (status 200).
- `POST /auth/create_users` → `create_user()`: recebe `UserSchema`, responde
  `UserPublic` (status 201).
- Ainda existe uma lista `database = []` no módulo, **declarada mas não usada** —
  ela será substituída pela `session` do SQLAlchemy.

### `server/database/schemas.py` — contratos Pydantic
- `UserSchema` (**entrada**): email, nome, senha, is_ativo, is_admin, time.
- `UserPublic` (**saída**): igual, mas **sem `senha`** → protege a senha.
- `EmailStr` valida automaticamente se o email é válido (vem do extra
  `pydantic[email]`).

### `server/database/models.py` — modelo ORM
- `User` mapeada para a tabela `users` via `@table_registry.mapped_as_dataclass`.
  Isso faz a classe virar uma **dataclass**, o que permite usar `asdict(user)`
  nos testes.
- Colunas: `user_id` (PK, `init=False` → gerada pelo banco), `user_email`
  (`unique=True`), `user_name`, `user_password`, `is_ativo`, `is_admin`,
  `user_time`, `created_at` (`init=False` + `server_default=func.now()`).
- `init=False` significa que o campo **não entra no construtor** — quem preenche
  é o banco.

> ⚠️ Atenção ao vocabulário: **model** (SQLAlchemy) = tabela do banco;
> **schema** (Pydantic) = contrato da API. São coisas diferentes e vivem em
> arquivos separados de propósito.

### `settings.py` — configuração
- `Settings(BaseSettings)` lê o `.env` via
  `SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')`.
- Expõe `DATABASE_URL: str` — como não tem valor padrão, é **obrigatória**:
  faltando no `.env`, o Pydantic levanta erro de validação na inicialização.
- O `.env` está no `.gitignore` (segredo não vai para o Git).

### `test/conftest.py` — fixtures do pytest
- `client`: `TestClient(app)` para testar a API sem servidor real.
- `session`: engine **SQLite em memória**, cria as tabelas (`create_all`),
  entrega a `Session` via `yield` e derruba as tabelas (`drop_all`) no fim —
  cada teste começa com um banco limpo.
- `_db_time_fake` / `return_mock`: context manager que registra um listener no
  evento `before_insert` do SQLAlchemy para forçar `created_at` com um valor
  fixo, deixando os testes de data/hora determinísticos.

### `test/test_app.py` — testes de integração (padrão AAA)
- `test_home`: GET `/auth` → 200 + mensagem esperada.
- `test_create_user`: POST `/auth/create_users` com payload válido → 201.

### `test/test_db.py` — teste do ORM
- Usa as fixtures `session` + `return_mock`.
- Cria um `User`, faz `session.add()` + `session.commit()`, lê de volta com
  `session.scalar(select(User).where(...))` e compara o resultado inteiro com
  `asdict(user)` — inclusive `created_at`, graças ao mock de tempo.

### `test/users/test_create_user.py` — reservado
- Ainda vazio (só a documentação). Destino dos testes de regra de negócio da
  criação de usuário.

### `alembic.ini` — configuração do Alembic
- `script_location = %(here)s/migrations` → onde estão os scripts de migração.
- `prepend_sys_path = .` → coloca a raiz do projeto no `sys.path`; é o que
  permite o `env.py` fazer `import settings` e
  `from server.database.models import table_registry`.
- `sqlalchemy.url = driver://user:pass@localhost/dbname` é apenas o **placeholder**
  criado pelo `alembic init` — ele é **sobrescrito em tempo de execução** pelo
  `env.py` com a URL do `.env`. Assim nenhum segredo fica no arquivo versionado.
- O resto do arquivo é configuração de **logging** (por isso `alembic` imprime
  aquelas linhas `INFO [alembic.runtime.migration] ...`).

### `migrations/env.py` — a ponte entre o Alembic e o projeto
- `config.set_main_option('sqlalchemy.url', settings.Settings().DATABASE_URL)`:
  injeta a URL do `.env` (via `pydantic-settings`) na config do Alembic.
- `target_metadata = table_registry.metadata`: entrega ao Alembic o *metadata* dos
  modelos. **É isso que habilita o `--autogenerate`** — ele compara esse metadata
  (o schema desejado) com o banco real (o schema atual) e gera o diff.
- `run_migrations_online()` (o caminho usado normalmente) abre uma conexão real;
  `run_migrations_offline()` só **gera o SQL** (usado com a flag `--sql`).

### `migrations/versions/3561799945aa_create_users_table.py` — 1ª revisão
- `revision = '3561799945aa'` e `down_revision = None` → é a **primeira** da
  corrente (não há nada antes dela).
- `upgrade()`: `op.create_table('users', ...)` com todas as colunas do modelo
  `User`, mais `PrimaryKeyConstraint('user_id')` e `UniqueConstraint('user_email')`.
- `downgrade()`: `op.drop_table('users')` — desfaz o que o `upgrade` fez.
- Detalhe de dialeto: o `created_at` saiu como
  `server_default=sa.text('(CURRENT_TIMESTAMP)')`. No modelo está `func.now()`;
  o Alembic traduziu para o SQL **do SQLite**. Em Postgres o texto gerado seria
  outro — migrations são específicas do banco.

### `migrations/GUIA-ALEMBIC.md` — guia de estudo da pasta
- Explica o papel de cada arquivo, o catálogo de comandos
  (`revision`/`upgrade`/`downgrade`/`current`/`history`/`stamp`/`--sql`), a
  inspeção com `uvx harlequin database.db`, o fluxo de trabalho e as armadilhas
  (renomear coluna, `NOT NULL` em tabela com dados, limitações do SQLite,
  nunca editar revisão já aplicada).

---

## 7. Comandos do dia a dia

```bash
task run      # sobe a API  -> uvicorn server.main:app --reload
task lint     # ruff check .
task format   # ruff format .
task test     # pytest -s -x --cov=server -vv
```

Detalhes das *tasks* (do `pyproject.toml`):
- `pre_run = 'task lint'` → sempre roda o lint antes de subir a API.
- `pre_test = 'task lint'` e `pre_format = 'ruff check --fix .'` → encadeamento
  automático via `pre_<task>`.

Flags do `task test`: `-s` (mostra `print`), `-x` (para no primeiro erro),
`--cov=server` (cobertura só do código da API), `-vv` (saída detalhada).

Configuração no `pyproject.toml`:
- **ruff**: `line-length = 79`, aspas simples, `preview = true`, regras
  `['I', 'F', 'E', 'W', 'PL', 'PT']` (imports, pyflakes, pycodestyle,
  warnings, pylint e pytest-style).
- **pytest**: `pythonpath = '.'` (permite `from server...` nos testes) e
  `addopts = '-p no:warnings'` (silencia warnings na saída).

### Migrations (Alembic)

Não há `task` para eles — rodam direto com `uv run`:

```bash
uv run alembic revision --autogenerate -m "descricao"  # cria a revisão (diff)
uv run alembic upgrade head       # aplica tudo o que falta
uv run alembic downgrade -1       # desfaz a última revisão (⚠️ apaga dados)
uv run alembic current            # em que revisão ESTE banco está
uv run alembic heads              # qual é a ponta da corrente no código
uv run alembic history -v         # histórico das revisões
uv run alembic upgrade head --sql # só imprime o SQL, sem executar
uv run alembic stamp head         # marca a revisão sem rodar o upgrade()
```

`head` = revisão mais nova; `base` = antes de tudo (`downgrade base` desfaz
**todas**).

### Inspecionar o banco

```bash
uvx harlequin database.db
```

`uvx` (= `uv tool run`) executa o **harlequin** — um cliente SQL de terminal — em
um ambiente temporário e isolado, **sem** adicioná-lo às dependências do projeto.
`database.db` é o arquivo SQLite apontado pelo `DATABASE_URL` (rode na raiz do
projeto). Dentro dele: `Ctrl+Enter`/`F5` executa a query, `Ctrl+Q` sai. Queries
úteis:

```sql
SELECT * FROM alembic_version;   -- em que revisão o banco está
SELECT * FROM users;             -- os dados
SELECT sql FROM sqlite_master WHERE name = 'users';  -- o CREATE TABLE gerado
```

### Git (versionar o código)

O Alembic versiona o **schema**; o git versiona o **código**. O ciclo de uma
alteração neste projeto:

```bash
git switch -c feat/minha-mudanca   # 1. branch nova a partir da main
# ... escreve o código ...
uv run task format                 # 2. formata
uv run task test                   # 3. lint (via pre_test) + testes
git status --short && git diff     # 4. revisa o que mudou
git add . && git commit -m "feat: descreve a mudança"
git push -u origin feat/minha-mudanca
git switch main && git merge feat/minha-mudanca   # 5. integra
git branch -d feat/minha-mudanca                  # 6. limpa
```

Mensagem de commit: resumo no **imperativo** (≤ 72 caracteres) com prefixo do
*Conventional Commits* (`feat:`, `fix:`, `test:`, `docs:`, `chore:`,
`refactor:`), linha em branco e corpo explicando **o porquê** — o *o quê* o
diff já mostra. Para várias linhas: repita o `-m` (um por parágrafo), rode
`git commit` sem `-m` (abre o editor) ou, no PowerShell, use um here-string
`@' ... '@`.

**Voltar versão** — o comando muda conforme o que se quer desfazer:

| Quero... | Comando |
|----------|---------|
| descartar edições não commitadas | `git restore .` |
| tirar da bandeja, mantendo a edição | `git restore --staged <arquivo>` |
| corrigir o último commit (ainda local) | `git commit --amend --no-edit` |
| desfazer o commit, manter as mudanças | `git reset --soft HEAD~1` |
| voltar a branch para um commit antigo | `git reset --hard <hash>` ⚠️ |
| desfazer um commit **já enviado** | `git revert <hash>` |
| achar um commit "perdido" | `git reflog` |

> Regra de ouro: `reset` **apaga** histórico → só em trabalho local; `revert`
> **acrescenta** um commit que anula o outro → é o correto depois do `push`.

Guardar trabalho pela metade: `git stash` / `git stash pop`.

> Guia completo de uv / taskipy / ruff / git em
> [comandos-uv-task-ruff.md](comandos-uv-task-ruff.md);
> de Alembic em [migrations/GUIA-ALEMBIC.md](../migrations/GUIA-ALEMBIC.md).

---

## 8. Documentação como parte do estudo

Regra do projeto (ver [CLAUDE.md](../CLAUDE.md)): **todo arquivo `.py`** —
inclusive os de teste — termina com um bloco
`========== DOCUMENTAÇÃO DO ARQUIVO ==========` descrevendo Utilidade, Imports,
Classes e Funções. Ao editar um arquivo, o bloco é **atualizado**, nunca
duplicado. A ideia é que o próprio código sirva de material de revisão.

---

## 9. Conceitos aprendidos até aqui

- **FastAPI**: `FastAPI()`, `APIRouter` com `prefix`/`tags`, rotas `async`,
  `status_code` (via `http.HTTPStatus`) e `response_model`.
- **Pydantic**: modelos de entrada vs. saída, validação automática, `EmailStr`,
  proteção de dados sensíveis via schema de resposta.
- **SQLAlchemy 2.0**: API declarativa moderna (`Mapped`, `mapped_column`,
  `registry`, `mapped_as_dataclass`), PK autogerada, `unique`, `server_default`,
  `select()`, `session.add/commit/scalar` e eventos (`before_insert`).
- **Alembic**: `alembic init`, `revision --autogenerate`, `upgrade head`,
  `downgrade -1`, `current`/`heads`/`history`, a tabela `alembic_version` dentro
  do banco, a corrente `down_revision` e o papel do `target_metadata` no
  autogenerate. Migration = *commit* do schema; `downgrade` = desfazer (apagando
  dados).
- **pydantic-settings**: configuração 12-factor via `.env`, com o `.env` fora
  do versionamento — reaproveitada pelo `migrations/env.py`.
- **uvx / uv tool run**: rodar ferramentas (ex.: `harlequin`) em ambiente
  temporário, sem poluir as dependências do projeto.
- **git**: as três áreas (working tree → staging → repositório), branches por
  feature, mensagens no padrão Conventional Commits e — o mais importante — a
  diferença entre `reset` (apaga histórico, só local) e `revert` (cria um
  commit que desfaz, seguro depois do `push`), com `reflog` como rede de
  segurança.
- **pytest**: padrão **AAA** (Arrange, Act, Assert), fixtures, `conftest.py`,
  `TestClient`, banco em memória isolado por teste e mock de tempo.
- **Tooling**: uv (ambiente/deps), ruff (lint+format), taskipy (atalhos),
  pytest-cov (cobertura).

---

## 10. Próximos passos sugeridos

```mermaid
graph LR
    A[Validar e devolver dados] --> M["Migrations com Alembic ✅"]
    M --> B[Conectar rota ao banco]
    B --> C[CRUD completo de usuário]
    C --> D[Hash de senha]
    D --> E[Login + JWT]
    E --> F[Rotas protegidas / permissões]
```

0. ~~**Migrations**: adotar **Alembic** para versionar o schema do banco.~~
   ✅ **feito** — tabela `users` criada pela revisão `3561799945aa` (passo 9).
1. **Ligar `settings.py` ao SQLAlchemy**: criar um módulo de conexão com
   `create_engine(Settings().DATABASE_URL)` e uma função `get_session()`. A
   tabela já existe no `database.db`; falta a aplicação abrir a conexão.
2. **Persistência real na rota**: injetar a `session` em `create_user` com
   `Depends(get_session)` e gravar o usuário (removendo a lista `database = []`).
   Nos testes, sobrescrever a dependência com
   `app.dependency_overrides[get_session]` para reaproveitar o SQLite em memória.
3. **CRUD**: listar, buscar por id, atualizar e deletar usuários.
4. **Segurança**: nunca salvar senha em texto puro — usar hash (ex.: `pwdlib`/
   `bcrypt`), validar email duplicado retornando 409/400. Cada mudança de coluna
   daqui em diante passa a exigir uma **nova migration**
   (`alembic revision --autogenerate`).
5. **Autenticação**: endpoint de login que devolve **JWT** e rotas protegidas.
6. **Testes**: completar `test/users/test_create_user.py` (email duplicado,
   campos inválidos, senha ausente) e cobrir os erros 422.
7. **Higiene do repo**: acrescentar `database.db` ao `.gitignore` — o banco é um
   artefato local; a fonte da verdade do schema é `migrations/versions/`.

<!--
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Documento de estudo que consolida todo o conhecimento e o código
    construído no projeto até o momento. Estrutura: visão geral do stack e do
    estágio atual; PASSO A PASSO (seção 2) que reconstrói o projeto na ordem
    em que cada peça nasceu — cada passo com o problema que resolve, o
    arquivo, o trecho de código, a lógica e como verificar — fechando com o
    fluxograma dos passos e a tabela-resumo "pergunta que cada peça
    responde"; diagramas de arquitetura e de fluxo de requisição; estrutura
    de pastas; resumo arquivo por arquivo; comandos e configurações; regra de
    documentação do projeto; conceitos aprendidos e roteiro de próximos
    passos. Inclui o passo 9 (MIGRATIONS com Alembic: alembic.ini,
    migrations/env.py, a revisão 3561799945aa que cria a tabela users, os
    comandos upgrade/downgrade e a inspeção do banco com
    `uvx harlequin database.db`), cujo detalhamento completo vive em
    migrations/GUIA-ALEMBIC.md. A seção 7 traz ainda o ciclo de trabalho com
    git (branch -> format -> test -> commit -> merge), o padrão de mensagem de
    commit e a tabela de "voltar versão" (restore / amend / reset / revert /
    reflog), detalhados em docs/comandos-uv-task-ruff.md.

Imports:
    Não se aplica (arquivo Markdown).

Classes:
    Não se aplica.

Funções:
    Não se aplica.
==========================================================================
-->
