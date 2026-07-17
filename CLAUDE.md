# CLAUDE.md

Guia para o Claude Code trabalhar neste projeto.

## Sobre o projeto

API construída com **FastAPI** (Python >= 3.13), usando **SQLAlchemy** para
persistência e **Pydantic** para validação. Gerenciado com **uv** e **taskipy**,
com lint/format via **ruff** e testes com **pytest**.

## Comandos

```bash
task run      # sobe a API (uvicorn server.main:app --reload)
task lint     # ruff check .
task format   # ruff format .
task test     # pytest -s -x --cov=server -vv
```

## Convenções

- `line-length = 79`, aspas simples (ruff format).
- Rotas em `server/routes/`, modelos/schemas em `server/database/`.
- Testes em `test/`.

> **Objetivo do projeto:** este é um projeto de **aprendizado** de como criar
> APIs com FastAPI *com tudo incluso* — ruff (lint/format), taskipy (tasks),
> pytest (testes), SQLAlchemy e Pydantic. Por isso a documentação abaixo vale
> para **todos** os arquivos `.py`, inclusive os de teste, para servirem de
> material de estudo.

## ⚠️ REGRA OBRIGATÓRIA — Documentação ao fim de cada arquivo

Sempre que você **criar ou editar** um arquivo de código (`.py`) deste projeto —
**incluindo os arquivos de teste** (`test/`, `conftest.py`, etc.) —
adicione (ou atualize) ao **final do arquivo** um bloco de documentação
descrevendo a utilidade do arquivo para o funcionamento da API.

O bloco deve ser um comentário/docstring no fim do arquivo com:

- **Utilidade:** o que o arquivo faz e seu papel na API.
- **Imports:** principais imports e por que são usados.
- **Classes:** cada classe e sua responsabilidade.
- **Funções:** cada função/rota, seus parâmetros e o que retorna.

Formato padrão a usar (docstring no fim do arquivo `.py`):

```python
"""
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    <descrição do papel do arquivo na API>

Imports:
    - <import>: <motivo do uso>

Classes:
    - <NomeClasse>: <responsabilidade>

Funções:
    - <nome_funcao(params)>: <o que faz / o que retorna>
==========================================================================
"""
```

Regras:
- Mantenha esse bloco **sempre no final** do arquivo.
- Ao editar um arquivo existente, **atualize** o bloco em vez de duplicá-lo.
- Se o arquivo já tiver o bloco, apenas mantenha-o em sincronia com o código.

<!--
========================= DOCUMENTAÇÃO DO ARQUIVO =========================
Utilidade:
    Arquivo de configuração e instruções do Claude Code para este projeto.
    Define stack, comandos, convenções e a regra obrigatória de documentar
    o fim de cada arquivo de código.

Imports:
    Não se aplica (arquivo Markdown).

Classes:
    Não se aplica.

Funções:
    Não se aplica.
==========================================================================
-->
