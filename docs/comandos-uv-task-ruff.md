# uv, taskipy (task), ruff e git — guia de comandos

Esse trio é a base de um projeto Python moderno:

- **uv** → gerencia Python, ambiente virtual e dependências (substitui pip, pyenv, poetry, virtualenv...).
- **ruff** → linter + formatador extremamente rápido (substitui flake8, isort, black...).
- **taskipy** → atalhos para comandos longos (o `task <nome>` que roda scripts definidos no `pyproject.toml`).

E, ao lado deles, o **git** — que versiona o *código* (assim como o Alembic
versiona o *schema* do banco). A seção 4 cobre commit, branch e como voltar
versão.

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

## 4. git — versionamento do código

O git guarda o histórico do projeto em **três áreas**. Entender isso explica
quase todos os comandos:

```
  working tree            staging (index)          repositório
  (seus arquivos)  --add-->  (o que vai   --commit-->  (histórico
                              no commit)                de commits)
```

- **working tree**: o que está no disco, do jeito que você editou.
- **staging/index**: a "bandeja" com o que entrará no próximo commit (`git add`).
- **repositório**: os commits já gravados (`git commit`).

### 4.1 Configuração inicial (uma vez por máquina)

```bash
git config --global user.name  "Seu Nome"
git config --global user.email "voce@email.com"
git config --global init.defaultBranch main   # nova branch padrão = main
git config --list                             # confere o que está configurado
```

### 4.2 Começar / clonar

```bash
git init                          # transforma a pasta atual em um repositório
git clone <url>                   # baixa um repositório existente
git clone <url> pasta-destino     # clona escolhendo o nome da pasta
git remote -v                     # mostra os remotos (origin) configurados
git remote add origin <url>       # liga o repo local a um remoto
```

> Depois de clonar um projeto Python: `uv sync` para recriar o ambiente e
> `cp .env.example .env` para criar as variáveis locais.

### 4.3 Ver o que mudou (antes de commitar)

```bash
git status                        # arquivos modificados / staged / não rastreados
git status --short                # versão compacta (M = modificado, A = novo, D = deletado)
git diff                          # mudanças AINDA NÃO adicionadas (working tree)
git diff --staged                 # mudanças JÁ adicionadas (o que vai no commit)
git diff --stat                   # só o resumo: arquivos + linhas alteradas
git diff main..minha-branch       # diferença entre duas branches
```

### 4.4 Adicionar e commitar

```bash
git add arquivo.py                # adiciona um arquivo específico
git add server/                   # adiciona uma pasta inteira
git add .                         # adiciona tudo que mudou (respeita o .gitignore)
git add -p                        # escolhe pedaço por pedaço o que vai entrar

git restore --staged arquivo.py   # tira da bandeja (desfaz o `add`, mantém a edição)

git commit -m "mensagem"          # grava o que está na bandeja
git commit -am "mensagem"         # add + commit de arquivos JÁ rastreados (não pega arquivo novo)
git commit                        # abre o editor (permite mensagem com corpo)
```

**Como escrever a mensagem**: 1ª linha = resumo curto (≤ 72 caracteres) no
**imperativo** ("Adiciona rota de login", não "Adicionado..."), linha em
branco, e o corpo explicando **o porquê** — o *o quê* o diff já mostra.

**Mensagem com várias linhas** — três formas:

```bash
# 1) um -m por parágrafo: o git separa cada um com uma linha em branco
git commit -m "feat: adiciona Alembic para migrations" -m "Configura o env.py lendo a DATABASE_URL do .env e cria a primeira revisão."

# 2) sem -m: abre o editor para escrever resumo + corpo com calma
git commit
```

```powershell
# 3) PowerShell (Windows): here-string com aspas simples preserva as quebras
#    de linha. O fechamento '@ TEM de estar na coluna 0.
git commit -m @'
feat: adiciona Alembic para migrations

- Configura migrations/env.py lendo a DATABASE_URL do Settings
- Cria a revisão inicial da tabela users
'@
```

> No bash/git-bash o equivalente é abrir aspas duplas e apertar Enter dentro
> delas: `git commit -m "resumo` ↵ ↵ `corpo"`.

Um padrão bastante usado é o *Conventional Commits*:

```bash
git commit -m "feat: adiciona endpoint de login com JWT"
git commit -m "fix: corrige 500 ao criar usuário sem email"
git commit -m "test: cobre criação de usuário no ORM"
git commit -m "docs: atualiza guia de comandos"
git commit -m "chore: adiciona alembic às dependências"
git commit -m "refactor: extrai get_session para database.py"
```

### 4.5 Histórico

```bash
git log                           # histórico completo
git log --oneline                 # um commit por linha (hash curto + resumo)
git log --oneline --graph --all   # desenha as branches e merges
git log -n 5                      # os 5 últimos
git log -p arquivo.py             # histórico COM o diff de um arquivo
git show <hash>                   # vê um commit específico por inteiro
git blame arquivo.py              # quem escreveu cada linha e em qual commit
```

### 4.6 Branches (trabalhar sem quebrar a `main`)

```bash
git branch                        # lista as branches locais (* = atual)
git branch -a                     # inclui as remotas
git switch -c feat/login          # CRIA e já muda para a nova branch
git switch main                   # volta para a main
git switch -                      # volta para a branch anterior

git branch -m novo-nome           # renomeia a branch atual
git branch -d feat/login          # apaga a branch (só se já foi mesclada)
git branch -D feat/login          # apaga à força (⚠️ perde os commits não mesclados)
```

> `git checkout -b feat/login` faz o mesmo que `git switch -c`. O `switch`
> (git ≥ 2.23) é a forma moderna e menos ambígua — `checkout` acumulava
> funções demais.

Convenção de nomes: `feat/`, `fix/`, `docs/`, `chore/` + descrição em
kebab-case (ex.: `feat/conectar-rota-ao-banco`).

### 4.7 Juntar o trabalho de volta

```bash
git switch main
git merge feat/login              # traz os commits da branch para a main
git merge --no-ff feat/login      # força um commit de merge (preserva o histórico da branch)
git merge --abort                 # cancela um merge que deu conflito
```

Em caso de **conflito**: o git marca o arquivo com `<<<<<<<`, `=======` e
`>>>>>>>`. Edite deixando o conteúdo final, depois `git add arquivo` e
`git commit`.

```bash
git rebase main                   # reaplica os commits da sua branch em cima da main
```

> ⚠️ `rebase` **reescreve** o histórico. Use só em branch local/sua; nunca em
> branch que outra pessoa já baixou.

### 4.8 Sincronizar com o remoto

```bash
git fetch                         # baixa as novidades SEM alterar seus arquivos
git pull                          # fetch + merge (atualiza a branch atual)
git pull --rebase                 # atualiza reaplicando seus commits por cima
git push                          # envia os commits da branch atual
git push -u origin feat/login     # 1º push de uma branch nova (cria e vincula)
git push --delete origin feat/login   # apaga a branch no remoto
```

### 4.9 Voltar versão / desfazer

Esta é a parte que mais confunde. A pergunta-chave é **o que você quer
desfazer**:

| Situação | Comando |
|----------|---------|
| Descartar a edição de um arquivo (não commitado) | `git restore arquivo.py` |
| Descartar **todas** as edições não commitadas | `git restore .` |
| Tirar da bandeja, mantendo a edição | `git restore --staged arquivo.py` |
| Corrigir a mensagem do último commit | `git commit --amend -m "nova mensagem"` |
| Esqueci um arquivo no último commit | `git add arquivo.py && git commit --amend --no-edit` |
| Desfazer o último commit, **mantendo** as mudanças na bandeja | `git reset --soft HEAD~1` |
| Desfazer o último commit, mantendo as mudanças fora da bandeja | `git reset HEAD~1` (= `--mixed`) |
| Desfazer o último commit e **jogar fora** as mudanças | `git reset --hard HEAD~1` ⚠️ |
| Desfazer um commit **já enviado** ao remoto | `git revert <hash>` |
| Voltar UM arquivo para como estava em um commit | `git restore --source=<hash> arquivo.py` |
| Ver o projeto inteiro em um commit antigo (só olhar) | `git checkout <hash>` → depois `git switch -` |

```bash
git reset --soft  HEAD~1     # desfaz o commit, mudanças ficam STAGED
git reset --mixed HEAD~1     # desfaz o commit, mudanças ficam no working tree (padrão)
git reset --hard  HEAD~1     # desfaz o commit E as mudanças  ⚠️ irreversível
git reset --hard <hash>      # volta a branch inteira para aquele commit
git revert <hash>            # cria um commit NOVO que anula o commit informado
```

**`reset` vs `revert`** — a regra de ouro:

- `reset` **apaga** commits do histórico → só em trabalho **local**, ainda não
  enviado (`push`).
- `revert` **acrescenta** um commit que desfaz o outro → é o correto quando o
  commit já está no remoto, porque não reescreve o que os outros já baixaram.

`HEAD` = o commit atual; `HEAD~1` = um commit antes; `HEAD~3` = três antes.

**Rede de segurança:**

```bash
git reflog                   # lista TUDO por onde o HEAD passou (inclusive o que "sumiu")
git reset --hard <hash>      # volta para um estado listado no reflog
```

Errou um `reset --hard`? O `reflog` quase sempre salva — ele guarda os hashes
por ~90 dias.

### 4.10 Guardar trabalho pela metade (stash)

```bash
git stash                    # guarda as mudanças e deixa a working tree limpa
git stash -u                 # inclui arquivos novos (untracked)
git stash list               # lista o que está guardado
git stash pop                # devolve as mudanças e remove da pilha
git stash apply              # devolve mas MANTÉM na pilha
git stash drop               # descarta o item guardado
```

Útil para: "preciso trocar de branch agora, mas não quero commitar isso ainda".

### 4.11 Tags (marcar versões)

```bash
git tag v0.1.0                        # tag simples no commit atual
git tag -a v0.1.0 -m "primeira versão"  # tag anotada (com autor e mensagem)
git tag                               # lista as tags
git push origin v0.1.0                # envia a tag para o remoto
git push --tags                       # envia todas
```

### 4.12 `.gitignore`

Lista o que **não** deve ser versionado. Neste projeto: `.env`, `.venv/`,
`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`, `database.db`.

```bash
git check-ignore -v arquivo      # descobre QUAL regra está ignorando o arquivo
git rm -r --cached __pycache__   # para de versionar algo que JÁ tinha sido commitado
```

> O `!` desfaz uma regra: `.env.*` ignora tudo, e `!.env.example` abre exceção
> para o arquivo de exemplo — que **deve** ser versionado, pois documenta as
> variáveis exigidas sem expor segredos.

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

### Ciclo de uma alteração (uv + task + git)

```bash
git switch -c feat/minha-mudanca   # 1. branch nova a partir da main
# ... escreve o código ...
uv run task format                 # 2. formata
uv run task test                   # 3. lint (via pre_test) + testes
git status && git diff             # 4. revisa o que mudou
git add . && git commit -m "feat: descreve a mudança"
git push -u origin feat/minha-mudanca
git switch main && git merge feat/minha-mudanca   # 5. integra
git branch -d feat/minha-mudanca                  # 6. limpa
```

Se algo der errado no meio: `git restore .` (descarta edições),
`git reset --soft HEAD~1` (desfaz o commit local) ou `git revert <hash>`
(desfaz um commit já enviado).

<!--
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Guia de referência dos comandos das ferramentas que sustentam o projeto:
    uv (ambiente, dependências e versões do Python), ruff (lint e format),
    taskipy (atalhos `task <nome>`) e git (versionamento do código:
    configuração, staging/commit, histórico, branches, merge/rebase, sincronia
    com o remoto, desfazer/voltar versão, stash, tags e .gitignore). Fecha com
    o fluxo típico de trabalho e o ciclo completo de uma alteração unindo as
    quatro ferramentas.

Imports:
    Não se aplica (arquivo Markdown).

Classes:
    Não se aplica.

Funções:
    Não se aplica.
==========================================================================
-->
