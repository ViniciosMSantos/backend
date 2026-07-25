# Guia da pasta `migrations/` — Alembic

> Material de estudo. Esta pasta é o **controle de versão do banco de dados**:
> assim como o Git guarda o histórico do *código*, o Alembic guarda o histórico
> do *schema* (tabelas, colunas, índices, constraints).

---

## 1. Para que serve

Sem Alembic, a única forma de criar as tabelas seria
`table_registry.metadata.create_all(engine)` — que só sabe criar o que **ainda
não existe**. Ele não sabe *alterar*: adicionar uma coluna, renomear, mudar tipo,
criar índice. Na prática, todo ambiente teria que apagar e recriar o banco a cada
mudança de modelo (perdendo dados).

O Alembic resolve isso guardando cada mudança de schema como um **arquivo Python
versionado** (uma *revision*), com duas funções:

| Função | O que faz | Comando |
|--------|-----------|---------|
| `upgrade()` | aplica a mudança (para frente) | `alembic upgrade` |
| `downgrade()` | desfaz a mudança (para trás) | `alembic downgrade` |

Cada revisão aponta para a anterior (`down_revision`), formando uma **corrente**.
O Alembic grava no próprio banco, na tabela `alembic_version`, **em qual revisão
aquele banco está**. É assim que ele sabe o que falta aplicar.

```mermaid
graph LR
    B[("banco<br/>alembic_version")] -.-> R1
    NONE["base<br/>(banco vazio)"] -->|upgrade| R1["3561799945aa<br/>create users table"]
    R1 -->|upgrade| R2["próxima revisão<br/>(futuro)"]
    R2 -->|downgrade| R1
    R1 -->|downgrade| NONE
```

---

## 2. Arquivos desta pasta

| Arquivo | Papel |
|---------|-------|
| `env.py` | **Script de configuração** que o Alembic executa antes de qualquer comando. Abre a conexão e diz quais metadados comparar. É o único arquivo que editamos à mão aqui. |
| `script.py.mako` | Template usado para gerar cada novo arquivo de revisão. |
| `versions/` | As revisões em si — o histórico do banco. Um arquivo por mudança. |
| `README` | Arquivo padrão criado pelo `alembic init` ("Generic single-database configuration"). |
| `GUIA-ALEMBIC.md` | Este guia. |

E fora da pasta, na raiz do projeto:

| Arquivo | Papel |
|---------|-------|
| `alembic.ini` | Configuração do Alembic: onde está a pasta de scripts (`script_location`), `prepend_sys_path = .` e config de logging. |
| `database.db` | O banco SQLite deste ambiente de estudo (apontado pelo `DATABASE_URL` do `.env`). |

### O que foi customizado no `env.py`

Duas linhas fazem toda a diferença — e são o que liga o Alembic ao **nosso**
projeto:

```python
# 1) usa a URL do .env (via pydantic-settings) em vez da do alembic.ini
config.set_main_option('sqlalchemy.url', settings.Settings().DATABASE_URL)

# 2) diz ao Alembic quais tabelas ele deve conhecer -> habilita o --autogenerate
target_metadata = table_registry.metadata
```

- **(1)** evita ter a URL (com senha, em projetos reais) escrita no
  `alembic.ini`, que é versionado. O `sqlalchemy.url = driver://user:pass@...`
  que continua no `.ini` é só o placeholder do `alembic init` — ele é
  **sobrescrito** em tempo de execução.
- **(2)** é o que permite o `--autogenerate`: o Alembic compara o
  `table_registry.metadata` (o *desejado*, definido em
  [server/database/models.py](../server/database/models.py)) com o banco real (o
  *atual*) e escreve o diff.

> O import `import settings` só funciona por causa do `prepend_sys_path = .` no
> `alembic.ini`, que coloca a raiz do projeto no `sys.path`.

---

## 3. Comandos principais

Todos rodam com `uv run` (para usar a venv do projeto).

### Criar uma revisão

```bash
# gera a revisão comparando models.py com o banco (o jeito usual)
uv run alembic revision --autogenerate -m "descricao curta"

# gera uma revisão VAZIA para escrever o SQL/ops à mão
uv run alembic revision -m "descricao curta"
```

O arquivo nasce em `versions/<hash>_descricao_curta.py`. **Sempre abra e revise**
antes de aplicar (ver seção 5).

### Aplicar (upgrade)

```bash
uv run alembic upgrade head      # aplica tudo o que falta (o mais comum)
uv run alembic upgrade +1        # aplica só a próxima revisão
uv run alembic upgrade 3561799945aa   # aplica até uma revisão específica
```

### Desfazer (downgrade)

```bash
uv run alembic downgrade -1      # desfaz a última revisão aplicada
uv run alembic downgrade base    # desfaz TUDO (volta ao banco vazio)
uv run alembic downgrade 3561799945aa  # volta até essa revisão
```

`head` = a ponta da corrente (revisão mais nova).
`base` = antes de tudo (nenhuma revisão aplicada).

> ⚠️ `downgrade` executa o `drop_table` / `drop_column` da revisão: **ele apaga
> dados**. Em produção só com backup; aqui, em estudo, é seguro e ótimo para
> testar se o `downgrade()` está correto.

### Inspecionar o estado

```bash
uv run alembic current      # em que revisão ESTE banco está
uv run alembic heads        # qual é a ponta da corrente no código
uv run alembic history      # histórico completo das revisões
uv run alembic history -v   # histórico detalhado
```

Se `current` == `heads`, banco e código estão sincronizados. Foi o que
verificamos aqui:

```
$ uv run alembic current
3561799945aa (head)
```

### Marcar sem executar

```bash
uv run alembic stamp head   # grava a revisão no banco SEM rodar o upgrade()
```

Usado quando o schema **já existe** (criado à mão ou por `create_all`) e você só
quer que o Alembic passe a considerar aquele banco como "já atualizado".

### Ver o SQL sem aplicar (modo offline)

```bash
uv run alembic upgrade head --sql       # imprime o SQL em vez de executar
uv run alembic upgrade head --sql > migration.sql
```

Ótimo para **entender** o que a revisão realmente faz — e, em empresas, para
mandar o SQL para um DBA revisar.

---

## 4. Inspecionar o banco: `uvx harlequin database.db`

Aplicar a migration é metade do aprendizado; a outra metade é **olhar o banco** e
confirmar que a tabela ficou como você esperava. Para isso usamos o
[Harlequin](https://harlequin.sh) — um cliente SQL que roda **no terminal** (TUI).

```bash
uvx harlequin database.db
```

O que cada parte faz:

- **`uvx`** = `uv tool run`: baixa e executa a ferramenta em um ambiente
  **temporário e isolado**. O Harlequin **não** entra como dependência do
  projeto (não vai para o `pyproject.toml`), o que é exatamente o desejado para
  uma ferramenta de inspeção.
- **`harlequin`** = a ferramenta.
- **`database.db`** = o arquivo SQLite a abrir (o mesmo do `DATABASE_URL`).
  Rode na **raiz do projeto**, onde o arquivo está.

Dentro do Harlequin:

| Tecla | Ação |
|-------|------|
| painel esquerdo | árvore de tabelas/colunas do banco |
| `Ctrl` + `Enter` (ou `F5`) | executa a query do editor |
| `F2` | foca o editor |
| `F10` | menu / ajuda |
| `Ctrl` + `Q` | sai |

Queries úteis para conferir o resultado das migrations:

```sql
-- em que revisão o banco está (a tabela que o Alembic mantém)
SELECT * FROM alembic_version;

-- quais tabelas existem
SELECT name FROM sqlite_master WHERE type = 'table';

-- o CREATE TABLE que o Alembic realmente gerou
SELECT sql FROM sqlite_master WHERE name = 'users';

-- os dados
SELECT * FROM users;
```

> Alternativa sem instalar nada: `sqlite3 database.db` (se disponível) ou a
> extensão SQLite do VS Code. O Harlequin é só mais confortável para navegar.

---

## 5. Fluxo de trabalho (o ciclo que você vai repetir)

```mermaid
graph LR
    A["1<br/>edita models.py"] --> B["2<br/>alembic revision<br/>--autogenerate"]
    B --> C["3<br/>LÊ o arquivo<br/>gerado"]
    C --> D["4<br/>alembic upgrade head"]
    D --> E["5<br/>uvx harlequin<br/>database.db"]
    E --> F["6<br/>task test"]
```

1. **Mudou o modelo** em `server/database/models.py` (nova coluna, nova tabela).
2. **Gerou** a revisão com `--autogenerate`.
3. **Leu** o arquivo em `versions/` — o autogenerate é um rascunho, não um
   oráculo.
4. **Aplicou** com `upgrade head`.
5. **Conferiu** no Harlequin.
6. **Rodou os testes** (`task test`) para garantir que nada quebrou.

E versionou no Git: o arquivo da revisão **entra no commit** junto com a mudança
do modelo. Migration e modelo andam sempre juntos — é isso que permite outra
pessoa (ou outro ambiente) chegar no mesmo schema rodando só `upgrade head`.

---

## 6. Armadilhas e cuidados

- **Nunca edite uma revisão já aplicada em outro ambiente.** Se ela já rodou
  fora da sua máquina, crie uma **nova** revisão corrigindo. Editar reescreve a
  história e os bancos ficam divergentes (é o mesmo problema de um
  `git rebase` em branch compartilhada).
- **O `--autogenerate` não detecta tudo.** Ele é bom em tabela/coluna nova,
  tabela/coluna removida e mudança de nullable/unique. É fraco em: **renomear**
  (ele vê como "dropar + criar", o que **perde os dados**), mudanças de tipo em
  alguns dialetos, `CHECK` constraints e nomes de constraint. Por isso o passo 3
  do fluxo — ler o arquivo — não é opcional.
- **SQLite tem `ALTER TABLE` limitado.** Ele não sabe dropar/alterar coluna
  direito; o Alembic contorna isso com `batch_alter_table` (recria a tabela). Em
  Postgres a mesma migration seria mais simples. É por isso que a coluna
  `created_at` aparece na revisão com `server_default=sa.text('(CURRENT_TIMESTAMP)')`
  em vez de `now()`: o SQL gerado é **específico do dialeto**.
- **`downgrade()` apaga dados.** Confira o que ele faz antes de rodar.
- **Coluna nova `NOT NULL` em tabela com dados quebra o upgrade.** As linhas
  existentes não têm valor. Solução: criar com `nullable=True`, preencher com um
  `UPDATE` na própria migration, e só então tornar `NOT NULL`.
- **Testes não usam Alembic.** A fixture `session` em
  [test/conftest.py](../test/conftest.py) usa `create_all` em SQLite em memória,
  porque é mais rápido e o objetivo do teste é o ORM, não o histórico de schema.
  Consequência prática: **um teste passando não prova que a migration está
  correta** — quem prova isso é o `upgrade`/`downgrade` no banco real.
- **`database.db` é um arquivo local de estudo.** Não deveria ir para o Git
  (vale acrescentá-lo ao `.gitignore`); a "fonte da verdade" do schema é a pasta
  `versions/`, não o arquivo do banco.
- **A pasta `migrations/` está fora do ruff** (`extend-exclude = ['migrations']`
  no `pyproject.toml`), porque os arquivos são gerados por template e não seguem
  o `line-length = 79` nem as aspas simples do projeto.

---

## 7. Referência rápida

```bash
# criar / aplicar
uv run alembic revision --autogenerate -m "add coluna x"
uv run alembic upgrade head

# desfazer
uv run alembic downgrade -1
uv run alembic downgrade base

# inspecionar
uv run alembic current
uv run alembic heads
uv run alembic history -v
uv run alembic upgrade head --sql     # só mostra o SQL

# olhar o banco
uvx harlequin database.db
```

<!--
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Guia de estudo da pasta `migrations/`. Explica por que o projeto usa
    Alembic (versionar o SCHEMA do banco, em vez de recriá-lo com
    create_all), o papel de cada arquivo da pasta (env.py, script.py.mako,
    versions/) e do alembic.ini na raiz, as duas customizações feitas no
    env.py (URL vinda do .env via Settings e target_metadata =
    table_registry.metadata, que habilita o --autogenerate), o catálogo de
    comandos (revision, upgrade, downgrade, current, heads, history, stamp,
    --sql), a inspeção do banco com `uvx harlequin database.db`, o fluxo de
    trabalho recomendado e as armadilhas mais comuns.

Imports:
    Não se aplica (arquivo Markdown).

Classes:
    Não se aplica.

Funções:
    Não se aplica.
==========================================================================
-->
