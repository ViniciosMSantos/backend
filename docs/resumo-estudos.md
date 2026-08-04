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

O ciclo está **fechado**: a requisição HTTP entra, é validada, **grava no banco
real** e volta serializada pelo schema de saída.

| Bloco | Situação |
|-------|----------|
| Rotas + schemas (`/auth`) | ✅ funcionando (valida entrada, devolve saída) |
| Modelo ORM (`User`) | ✅ definido e **testado** |
| Configuração (`Settings`) | ✅ lê o `.env` e alimenta a engine em `db.py` |
| Migrations (Alembic) | ✅ tabela `users` criada no `database.db` (revisão `3561799945aa`) |
| Conexão + sessão (`db.py`) | ✅ `create_engine` + `get_session` |
| Sessão na rota | ✅ `Depends(get_session)` em `create_user` e `read_users` |
| Persistência de verdade | ✅ `POST /auth/create_users` grava; `GET /auth/users` lê |
| Testes contra a rota | ✅ `dependency_overrides` troca o banco pelo SQLite em memória |
| Senha | ⚠️ salva em **texto puro** — falta hash (próximo passo) |

Ou seja: o que antes eram três peças isoladas (modelo, configuração e rota)
agora está conectado por `db.py`. A API grava no `database.db` — cujo schema foi
criado pelo Alembic — e os testes exercitam essa mesma rota apontando para um
SQLite em memória, sem tocar no banco de desenvolvimento. O elo que falta agora
é de **segurança**, não de encanamento (ver seção 10).

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
    P9 --> P10["10<br/>Ligar rota<br/>ao banco ✅"]
    P10 --> P11["11<br/>Hash de senha<br/>+ login ⏳"]
```

> Os passos 1 a 10 estão **feitos** e cada um tem sua seção abaixo. O passo 11 é
> o próximo da fila e está detalhado na
> [seção 10 — próximos passos](#10-próximos-passos-sugeridos).

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
    return usuario_schema      # nesta etapa ainda não havia banco
```

**Lógica:** `UserPublic` é o `UserSchema` **sem `senha`**. Mesmo a função
devolvendo o objeto completo, o `response_model` faz o FastAPI serializar
**apenas** os campos declarados. A proteção não depende de eu lembrar de remover
a senha — está no contrato.

**Como sei que deu certo:** o 201 volta sem o campo `senha`.

> No passo 10 esta mesma rota passa a devolver o objeto do **ORM** em vez do
> schema de entrada. O `response_model` não muda — mas o `UserPublic` ganha os
> `validation_alias`, porque os nomes das colunas são diferentes dos campos do
> JSON.

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

### Passo 10 — Ligar a rota ao banco ✅

**Problema:** até aqui os passos 6 e 7 viviam **isolados** — o `User` só era
usado nos testes e nenhum `create_engine` lia o `Settings` (só o `env.py` do
Alembic). A tabela já existia no `database.db`, mas a API não escrevia nela:
`create_user` validava e devolvia o próprio payload.

#### 10.1 — O módulo de conexão

**Arquivo:** [server/database/db.py](../server/database/db.py) *(novo)*

```python
engine = create_engine(Settings().DATABASE_URL)


def get_session():
    with Session(engine) as session:
        yield session
```

**Lógica:** a `engine` (o **pool de conexões**) é criada **uma vez**, quando o
módulo é importado — abrir conexão por requisição seria caro. Já a `Session` é
**por requisição**: ela guarda os objetos pendentes até o `commit`, então
compartilhá-la entre requisições misturaria transações.

O `yield` em vez de `return` é o detalhe importante: é ele que transforma a
função em uma **dependência com teardown**. Tudo antes do `yield` é setup, tudo
depois roda quando a resposta já saiu — e o `with` garante que a conexão volta
ao pool mesmo se a rota levantar exceção.

#### 10.2 — Injetar a sessão na rota (`Depends`)

```python
async def create_user(usuario_schema: UserSchema, session=Depends(get_session)):
```

**Lógica:** `Depends` é **injeção de dependência**. A rota não cria a Session,
ela **pede** uma — e quem decide de onde ela vem é o FastAPI. Por isso a rota
não sabe (nem precisa saber) se está falando com o `database.db` ou com um
SQLite em memória; é exatamente essa indireção que torna o passo 10.5 possível.

#### 10.3 — Gravar: schema → model → banco

```python
db_user = session.scalar(
    select(User).where(User.user_email == usuario_schema.email)
)
if db_user:
    raise HTTPException(
        status_code=HTTPStatus.CONFLICT, detail='E-mail já cadastrado.'
    )

db_user = User(user_email=usuario_schema.email, ...)   # schema -> model
session.add(db_user)        # marca como pendente (ainda não há SQL)
session.commit()            # dispara o INSERT
session.refresh(db_user)    # relê as colunas geradas pelo banco
```

**Lógica:** aqui acontece a **conversão** que o passo 6 já anunciava —
`UserSchema` (contrato do cliente) vira `User` (linha da tabela), campo por
campo, porque os nomes são diferentes de propósito.

Três pontos que valem virar hábito:

- **A checagem de e-mail duplicado é para dar erro BOM.** O `unique=True` da
  coluna já impediria o registro repetido, mas o erro viria como uma exceção do
  banco (`IntegrityError` → 500). Consultar antes permite responder **409
  CONFLICT** com uma mensagem clara. O `unique` continua sendo a garantia final.
- **`add()` não grava; `commit()` grava.** O `add` só coloca o objeto na fila da
  sessão.
- **`refresh()` traz de volta o que o BANCO gerou.** `user_id` e `created_at`
  são `init=False` — não existem no objeto em memória até o banco preenchê-los.
  Sem o `refresh`, o `id` da resposta não estaria disponível.

#### 10.4 — Ler do ORM na resposta: os `validation_alias`

**Problema novo:** agora a rota devolve um objeto do **SQLAlchemy**, não mais um
schema Pydantic. E as colunas se chamam `user_email`, `user_name`, `user_time`,
`user_id` — não `email`, `nome`, `time`, `id`.

```python
class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

    id: int = Field(validation_alias='user_id')
    email: EmailStr = Field(validation_alias='user_email')
    nome: str = Field(validation_alias='user_name')
    is_ativo: bool
    is_admin: bool
    time: str = Field(validation_alias='user_time')
```

**Lógica:** `from_attributes=True` autoriza o Pydantic a ler o objeto **por
atributo** (`user.user_email`) em vez de por chave de dicionário. O
`validation_alias` diz **de onde ler**; o nome do campo continua sendo o que
aparece no JSON. Resultado: o banco mantém seus nomes prefixados e o cliente
recebe `{'id': 1, 'email': ..., 'nome': ..., 'time': ...}`.

`is_ativo` e `is_admin` não precisam de alias — coluna e campo têm o mesmo nome.

> ### ⚠️ Armadilha que apareceu na prática
>
> O campo `id` foi declarado **sem** o alias:
>
> ```python
> id: int          # Pydantic procura user.id -> não existe!
> ```
>
> A resposta virou **500** com
> `ResponseValidationError: ('response', 'id') Field required`.
>
> O que isso ensina: a validação do `response_model` acontece **depois** do
> `commit()`. O usuário **foi gravado no banco** e o cliente recebeu erro — o
> tipo de bug que faz parecer que "não salvou", quando salvou. Erro de
> *resposta* é 500 (culpa do servidor); erro de *entrada* é 422 (culpa do
> cliente).
>
> Correção: `id: int = Field(validation_alias='user_id')`.

#### 10.5 — Listar usuários (`UserList`)

```python
@auth_router.get('/users', status_code=HTTPStatus.OK, response_model=UserList)
def read_users(limit: int = 10, offset: int = 1, session=Depends(get_session)):
    users = session.scalars(select(User).limit(limit).offset(offset)).all()
    return {'users': users}
```

**Lógica:** `scalar()` (singular) devolve **um** objeto ou `None`; `scalars()`
(plural) devolve um iterável, e o `.all()` o materializa em lista.

`limit`/`offset` são só parâmetros com valor padrão — o FastAPI os expõe
automaticamente como **query string** (`/auth/users?limit=5&offset=0`), porque
não aparecem no caminho da rota.

`UserList` envelopa a lista em `{'users': [...]}` em vez de devolver um array
puro. Assim é possível somar `total`/`página` depois sem quebrar quem já
consome a API.

> ⚠️ O `offset` está com padrão **1**, então a primeira página pula o primeiro
> usuário. O correto é `0` — anotado nos próximos passos.

#### 10.6 — Fazer os testes usarem um banco descartável

**Problema:** com a rota gravando de verdade, `test_create_user` passaria a
escrever no banco de **desenvolvimento**.

**Arquivo:** [test/conftest.py](../test/conftest.py)

```python
@pytest.fixture
def client(session):
    def get_session_override():
        return session

    with TestClient(app) as client:
        app.dependency_overrides[get_session] = get_session_override
        yield client

    app.dependency_overrides.clear()
```

**Lógica:** `app.dependency_overrides` é o mecanismo oficial do FastAPI para
**trocar uma dependência nos testes**. A chave é a função original
(`get_session`); o valor é a substituta. Onde a rota pedir `Depends(get_session)`,
recebe a Session em memória.

- O override usa `return`, não `yield` — quem fecha a Session é a fixture
  `session`.
- O `.clear()` no fim é **obrigatório**: `dependency_overrides` vive no objeto
  `app`, que é global. Sem limpar, o override vazaria para os testes seguintes.
- `client` agora **declara `session` como parâmetro** — é isso que garante que o
  banco em memória exista antes do client.

E a engine de teste ganhou dois argumentos:

```python
engine = create_engine(
    'sqlite:///:memory:',
    connect_args={'check_same_thread': False},
    poolclass=StaticPool,
)
```

- **`StaticPool`** força o pool a reusar **sempre a mesma conexão**. Cada
  conexão nova para `:memory:` abriria um banco **novo e vazio** — as tabelas
  criadas pela fixture não existiriam para a rota (`no such table: users`).
- **`check_same_thread=False`** porque o SQLite, por padrão, proíbe usar a
  conexão fora da thread que a criou — e o `TestClient` roda o app em outra
  thread.

**Como sei que deu certo:**

```bash
uv run task test                      # 3 passed
uvx harlequin database.db             # SELECT * FROM users; -> o registro está lá
```

E via `/docs`: `POST /auth/create_users` devolve 201 com `id`; repetir o mesmo
e-mail devolve **409**; `GET /auth/users` lista o que foi gravado.

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
| 10 | `db.py` + `Depends` | *Como o dado sobrevive ao restart?* | A rota **pede** uma Session em vez de criar uma; `add`+`commit` gravam e o `response_model` traduz as colunas de volta para o JSON. |

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
        S["server/database/schemas.py<br/>Pydantic: UserSchema /<br/>UserPublic / UserList"]
        MO["server/database/models.py<br/>SQLAlchemy: User"]
        CN["server/database/db.py<br/>engine + get_session"]
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
    R -->|resposta UserPublic / UserList| C
    R -->|Depends: pede a Session| CN
    R -->|monta/lê objetos| MO
    CN -->|abre conexão| DB
    CN -.->|dependency_overrides nos testes| TDB
    MO -->|metadata comparado por| AL
    CFG -->|DATABASE_URL| CN
    CFG -->|DATABASE_URL| AL
    AL --> VER
    VER -->|upgrade cria a tabela| DB
```

> O ciclo está completo: `db.py` é a peça que uniu `settings.py` (a URL),
> `models.py` (as tabelas) e as rotas. A única seta **tracejada** é a dos
> testes — ela só existe quando o `app.dependency_overrides` substitui o
> `get_session`, apontando as mesmas rotas para o SQLite em memória. O Alembic
> continua num caminho paralelo: ele cuida do **schema**, a aplicação cuida dos
> **dados**.

---

## 4. Fluxo de uma requisição (criar usuário)

```mermaid
sequenceDiagram
    participant Cli as Cliente
    participant App as FastAPI (main)
    participant Dep as get_session (db.py)
    participant Rt as auth_router
    participant In as UserSchema (Pydantic)
    participant DB as Banco (SQLAlchemy)
    participant Out as UserPublic (Pydantic)

    Cli->>App: POST /auth/create_users (JSON)
    App->>In: valida campos e tipos
    alt dados inválidos
        In-->>Cli: 422 Unprocessable Entity
    else dados válidos
        App->>Dep: resolve a dependência
        Dep->>App: Session aberta
        App->>Rt: chama create_user(schema, session)
        Rt->>DB: SELECT ... WHERE user_email = ?
        alt e-mail já existe
            DB-->>Rt: usuário encontrado
            Rt-->>Cli: 409 CONFLICT
        else e-mail livre
            Rt->>DB: add + commit (INSERT) + refresh
            DB-->>Rt: User com user_id e created_at
            Rt->>Out: response_model lê via validation_alias
            Out-->>Cli: 201 CREATED (com id, sem senha)
        end
        Dep->>Dep: fecha a Session (pós-yield)
    end
```

Três pontos-chave deste fluxo:

1. **Entra `UserSchema` (com senha), sai `UserPublic` (sem senha).** A senha não
   vaza porque o `response_model` serializa **apenas** os campos declarados.
2. **A validação de entrada acontece antes da rota** (422 = culpa do cliente); a
   do `response_model`, **depois do commit** (500 = culpa do servidor). Foi
   exatamente aí que o bug do `id` sem alias apareceu.
3. **A Session é fechada no fim**, no código que vem depois do `yield` do
   `get_session` — inclusive se a rota tiver levantado o 409.

---

## 5. Estrutura de pastas

```
fastapi_1/
├── server/                     # código da aplicação
│   ├── main.py                 # ponto de entrada: cria app e inclui routers
│   ├── routes/
│   │   └── auth_routes.py       # rotas /auth (home, create_users, users)
│   └── database/
│       ├── db.py                # engine + get_session (conexão com o banco)
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
- `POST /auth/create_users` → `create_user()`: recebe `UserSchema`, checa e-mail
  duplicado (**409**), grava com `add`+`commit`+`refresh` e responde `UserPublic`
  (status 201).
- `GET /auth/users` → `read_users()`: lista paginada com `limit`/`offset` (query
  string), responde `UserList` (status 200).
- Ambas recebem a Session via `session=Depends(get_session)`.
- A lista `database = []` continua no módulo, agora **totalmente sem uso** —
  ficou como resquício da fase pré-banco e pode ser removida.

### `server/database/db.py` — conexão com o banco
- `engine = create_engine(Settings().DATABASE_URL)`: criada **uma vez** por
  import; é o pool de conexões compartilhado pela aplicação.
- `get_session()`: generator usado como dependência (`Depends`). Abre a
  `Session`, entrega via `yield` e fecha depois da resposta.
- É a peça que faltava para unir `settings.py` (URL), `models.py` (tabelas) e as
  rotas. Também é o **ponto de substituição** nos testes, via
  `app.dependency_overrides`.

### `server/database/schemas.py` — contratos Pydantic
- `UserSchema` (**entrada**): email, nome, senha, is_ativo, is_admin, time.
- `UserPublic` (**saída**): sem `senha` e com `id`. Usa
  `ConfigDict(from_attributes=True)` para ler o objeto do ORM por atributo, e
  `Field(validation_alias=...)` para mapear `user_id`/`user_email`/`user_name`/
  `user_time` nos campos `id`/`email`/`nome`/`time` do JSON.
- `UserList` (**saída da listagem**): envelopa a lista em `{'users': [...]}`.
  Herda de `BaseModel` porque o FastAPI só aceita tipos Pydantic em
  `response_model` — uma classe comum gera
  `FastAPIError: Invalid args for response field!`.
- `EmailStr` valida automaticamente se o email é válido (vem do extra
  `pydantic[email]`).

> ⚠️ Cada campo cujo nome difere da coluna **precisa** do `validation_alias`.
> Faltando um, o Pydantic não encontra o atributo no objeto do ORM e a API
> responde **500** (`ResponseValidationError`) — depois de já ter gravado.

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
- É consumida em **dois lugares**: `server/database/db.py` (a engine da
  aplicação) e `migrations/env.py` (a URL usada pelo Alembic).
- O `.env` está no `.gitignore` (segredo não vai para o Git).

### `test/conftest.py` — fixtures do pytest
- `client(session)`: `TestClient(app)` já apontando para o banco de **teste**.
  Registra `app.dependency_overrides[get_session]` para as rotas receberem a
  Session em memória em vez da real, e chama `.clear()` no teardown — sem isso o
  override vazaria para os outros testes, porque `app` é global.
- `session`: engine **SQLite em memória** (com `StaticPool` e
  `check_same_thread=False`, necessários para o TestClient ver as mesmas
  tabelas), cria as tabelas (`create_all`), entrega a `Session` via `yield` e
  derruba as tabelas (`drop_all`) no fim — cada teste começa com um banco limpo.
- `_db_time_fake` / `return_mock`: context manager que registra um listener no
  evento `before_insert` do SQLAlchemy para forçar `created_at` com um valor
  fixo, deixando os testes de data/hora determinísticos.

### `test/test_app.py` — testes de integração (padrão AAA)
- `test_home`: GET `/auth` → 200 + mensagem esperada.
- `test_create_user`: POST `/auth/create_users` com payload válido → 201. Como o
  `client` aponta para o banco em memória, este teste hoje exercita a rota
  **inteira** — validação, INSERT e serialização da resposta. Foi ele que acusou
  o `id` sem `validation_alias` (500 em vez de 201).
- Ainda sem cobertura: 409 de e-mail repetido, `GET /auth/users` e a conferência
  do **corpo** da resposta do create (só o status é verificado).

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
  `status_code` (via `http.HTTPStatus`), `response_model`, `HTTPException` para
  erros de negócio (409) e parâmetros com valor padrão virando **query string**
  (`limit`/`offset`).
- **Injeção de dependência**: `Depends(get_session)` — a rota **pede** o recurso
  em vez de criá-lo. Dependência com `yield` = setup + teardown automáticos. E
  `app.dependency_overrides` para substituí-la nos testes, o que só é possível
  justamente porque a rota não sabe de onde o recurso vem.
- **Pydantic**: modelos de entrada vs. saída, validação automática, `EmailStr`,
  proteção de dados sensíveis via schema de resposta, `ConfigDict(
  from_attributes=True)` para ler objetos do ORM e `Field(validation_alias=...)`
  para traduzir nomes de coluna em nomes de campo do JSON.
- **Onde cada erro nasce**: 422 = entrada inválida (antes da rota rodar); 409 =
  conflito de regra de negócio (levantado por mim); 500
  `ResponseValidationError` = o `response_model` não conseguiu ler o objeto
  devolvido — e acontece **depois** do commit, então o dado já está no banco.
- **SQLAlchemy 2.0**: API declarativa moderna (`Mapped`, `mapped_column`,
  `registry`, `mapped_as_dataclass`), PK autogerada, `unique`, `server_default`,
  `select()`, `session.add/commit/scalar` e eventos (`before_insert`).
  Diferenças que importam: `add()` enfileira e `commit()` grava; `refresh()`
  traz de volta o que o banco gerou (`user_id`, `created_at`); `scalar()`
  devolve um objeto ou `None` e `scalars()` devolve vários (com `.all()`).
  `engine` é criada uma vez (pool), `Session` é por requisição.
- **SQLite em memória com TestClient**: `StaticPool` (senão cada conexão abre um
  banco novo e vazio) + `check_same_thread=False` (o app roda em outra thread).
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
    M --> B["Conectar rota ao banco ✅"]
    B --> C[CRUD completo de usuário]
    C --> D[Hash de senha]
    D --> E[Login + JWT]
    E --> F[Rotas protegidas / permissões]
```

0. ~~**Migrations**: adotar **Alembic** para versionar o schema do banco.~~
   ✅ **feito** — tabela `users` criada pela revisão `3561799945aa` (passo 9).
1. ~~**Ligar `settings.py` ao SQLAlchemy**: módulo de conexão com
   `create_engine(Settings().DATABASE_URL)` e `get_session()`.~~
   ✅ **feito** — [server/database/db.py](../server/database/db.py) (passo 10.1).
2. ~~**Persistência real na rota**: injetar a `session` com `Depends`, gravar o
   usuário e, nos testes, usar `app.dependency_overrides[get_session]`.~~
   ✅ **feito** — `create_user` grava e `read_users` lista (passo 10).

**A fazer, em ordem de prioridade:**

3. **Corrigir o `offset`**: o padrão é `1` em `read_users`, deveria ser `0` —
   hoje a primeira página pula o primeiro usuário.
4. **Segurança (o mais urgente)**: a senha está sendo salva em **texto puro** em
   `user_password`. Usar hash (`pwdlib`/`argon2` ou `bcrypt`) na criação e nunca
   guardar o valor original. Trocar o tamanho/nome da coluna daqui em diante
   exige uma **nova migration** (`alembic revision --autogenerate`).
5. **Completar o CRUD**: buscar por id (`GET /auth/users/{id}`), atualizar
   (`PUT`/`PATCH`) e deletar (`DELETE`) — cada um com 404 quando o usuário não
   existe.
6. **Testes**: cobrir o **409** de e-mail duplicado, o `GET /auth/users` (lista
   vazia e com dados), os erros **422** e o corpo das respostas — não só o
   status. Preencher `test/users/test_create_user.py`, que segue só com o bloco
   de documentação.
7. **Limpeza**: remover a lista `database = []` de `auth_routes.py`, que ficou
   sem uso depois do passo 10.
8. **Autenticação**: endpoint de login que devolve **JWT** e rotas protegidas por
   permissão (`is_admin`).
9. **Fábrica de dados nos testes**: com mais casos, criar usuário na mão em cada
   teste vira repetição — vale uma fixture/factory (ex.: `factory-boy`).

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
    migrations/GUIA-ALEMBIC.md. O passo 10 fecha o ciclo da API: o módulo de
    conexão server/database/db.py (engine + get_session), a INJEÇÃO DE
    DEPENDÊNCIA com Depends na rota, a gravação schema -> model -> banco
    (add/commit/refresh) com 409 para e-mail duplicado, os validation_alias
    do UserPublic para ler o objeto do ORM (e a armadilha do campo `id` sem
    alias, que gera 500 ResponseValidationError DEPOIS do commit), a rota de
    listagem com UserList + limit/offset e a troca do banco nos testes via
    app.dependency_overrides (com StaticPool e check_same_thread=False).
    A seção 7 traz ainda o ciclo de trabalho com
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
