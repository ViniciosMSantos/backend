# uv, taskipy (task) e ruff — guia de comandos

Esse trio é a base de um projeto Python moderno:

- **uv** → gerencia Python, ambiente virtual e dependências (substitui pip, pyenv, poetry, virtualenv...).
- **ruff** → linter + formatador extremamente rápido (substitui flake8, isort, black...).
- **taskipy** → atalhos para comandos longos (o `task <nome>` que roda scripts definidos no `pyproject.toml`).

---

## 1. uv — gerenciador de projeto e dependências

### Criando / iniciando projeto

```bash
uv init nome-do-projeto      # cria a pasta com pyproject.toml, .python-version e main.py
uv init                      # inicializa dentro de uma pasta já existente
uv init --app                # aplicação (padrão)
uv init --lib                # biblioteca (gera estrutura src/)
uv init --python 3.12        # já fixa a versão do Python
```

### Dependências

```bash
uv add requests              # adiciona pacote (instala + registra no pyproject.toml)
uv add ruff pytest taskipy   # vários de uma vez
uv add "fastapi[standard]"   # com extras
uv add --dev ruff pytest     # dependência de desenvolvimento (grupo dev)
uv add -r requirements.txt   # importa de um requirements.txt

uv remove requests           # remove pacote
uv sync                      # instala Python + cria venv + instala TUDO do lock (1 comando)
uv lock                      # atualiza o uv.lock sem instalar
uv tree                      # mostra a árvore de dependências
```

> `uv sync` é o comando que você roda ao clonar um projeto: ele reconstrói o ambiente inteiro de forma reproduzível a partir do `uv.lock`.

### Rodando código

```bash
uv run main.py               # executa sem precisar ativar a venv
uv run python                # abre o REPL dentro do ambiente
uv run pytest                # roda qualquer comando dentro da venv
uv run task test             # roda uma task do taskipy (ver seção 3)
```

### Gerenciando versões do Python

```bash
uv python list               # lista instaladas + disponíveis para baixar
uv python install 3.13       # baixa e instala uma versão
uv python install 3.11 3.12  # várias de uma vez
uv python pin 3.12           # fixa a versão do projeto (cria/atualiza .python-version)
uv python find               # mostra qual Python será usado aqui
uv python uninstall 3.10     # remove uma versão
```

### Ferramentas globais (tipo pipx)

```bash
uv tool install ruff         # instala a ferramenta de forma isolada e global
uvx ruff check .             # roda uma ferramenta SEM instalar (efêmero) — atalho de "uv tool run"
uv tool list                 # lista ferramentas instaladas
uv tool uninstall ruff       # remove
```

---

## 2. ruff — linter e formatador

O ruff faz dois trabalhos: **verificar** (lint) e **formatar** (format).

```bash
uv run ruff check .          # analisa o código em busca de problemas
uv run ruff check . --fix    # corrige automaticamente o que for possível
uv run ruff check . --watch  # fica observando arquivos e re-analisa ao salvar

uv run ruff format .         # formata o código (equivalente ao black)
uv run ruff format . --check # só verifica se está formatado, sem alterar (ótimo para CI)
```

> Regra prática do dia a dia: `ruff check --fix` para arrumar imports/erros e `ruff format` para padronizar o estilo.

### Configuração no `pyproject.toml`

```toml
[tool.ruff]
line-length = 79

[tool.ruff.lint]
preview = true
select = ['I', 'F', 'E', 'W', 'PL', 'PT']

[tool.ruff.format]
preview = true
quote-style = 'single'
```

Principais grupos de regras em `select`:

| Código | O que verifica |
|--------|----------------|
| `E`/`W` | Erros e avisos de estilo (pycodestyle) |
| `F` | Erros lógicos (pyflakes) — variável não usada, import faltando |
| `I` | Ordenação de imports (isort) |
| `PL` | Regras do Pylint |
| `PT` | Boas práticas de testes (flake8-pytest-style) |

---

## 3. taskipy (task) — atalhos de comandos

O taskipy deixa você criar apelidos para comandos longos. Você define as tasks no `pyproject.toml` e roda com `task <nome>`.

### Instalação

```bash
uv add --dev taskipy
```

### Definindo tasks no `pyproject.toml`

```toml
[tool.taskipy.tasks]
lint = 'ruff check .'
format = 'ruff format .'
run = 'python main.py'
pre_test = 'task lint'
test = 'pytest -s -x --cov=. -vv'
post_test = 'coverage html'
```

### Executando

```bash
uv run task lint             # roda o "ruff check ."
uv run task test             # roda a suíte de testes
uv run task run              # roda a aplicação
```

Detalhes úteis:

- **`pre_<task>` e `post_<task>`**: rodam automaticamente antes/depois. No exemplo acima, `task test` executa `pre_test` (lint) → `test` → `post_test` (relatório de cobertura) em sequência.
- Uma task pode chamar outra: `pre_test = 'task lint'`.
- Se você ativou a venv (`.venv`), pode rodar só `task test` sem o `uv run` na frente.

---

## Fluxo típico de trabalho

```bash
uv init meu-projeto              # 1. cria o projeto
cd meu-projeto
uv add --dev ruff pytest taskipy # 2. adiciona ferramentas de dev
# ... define as tasks no pyproject.toml ...
uv run task format               # 3. formata o código
uv run task lint                 # 4. verifica problemas
uv run task test                 # 5. roda os testes
```

Ao clonar um projeto já existente, basta:

```bash
uv sync                          # recria o ambiente inteiro a partir do lock
```
