"""
Módulo: core/page.py
=====================
Define a estrutura de página (Page) e a função que divide registros em páginas.

O que é uma página de banco de dados?
--------------------------------------
Em um SGBD real, os dados não são armazenados registro a registro no disco —
eles são agrupados em blocos de tamanho fixo chamados PÁGINAS. Quando o banco
de dados lê um registro, ele lê a página inteira de uma vez (isso é chamado de
"I/O de página").

Nesta simulação:
- Cada página armazena no máximo PAGE_SIZE palavras.
- As páginas são numeradas sequencialmente (page_id = 0, 1, 2, ...).
- A última página pode ter menos registros que PAGE_SIZE.
- O índice hash armazena, para cada palavra, o page_id da página onde ela está.

Custo de I/O:
- Uma busca por índice lê exatamente 1 página (a página onde a palavra está).
- Um table scan pode ler de 1 até N páginas (onde N = total de páginas).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Page:
    """
    Representa uma página de dados no banco de dados simulado.

    Attributes:
        page_id: Identificador único da página, 0-indexed.
                 Ex: page_id=0 é a primeira página, page_id=4665 é a última
                 para um arquivo de ~466k palavras com PAGE_SIZE=100.
        records: Lista de strings (palavras) armazenadas nesta página.
                 Tamanho máximo = PAGE_SIZE (pode ser menor na última página).
    """

    page_id: int
    records: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"Page(id={self.page_id}, "
            f"registros={len(self.records)}, "
            f"primeiro='{self.records[0] if self.records else ''}', "
            f"último='{self.records[-1] if self.records else ''}')"
        )


def build_pages(words: list[str], page_size: int) -> list[Page]:
    """
    Divide uma lista de palavras em páginas de tamanho fixo.

    Percorre a lista em passos de `page_size` e cria uma Page para cada fatia.
    A última página pode ter menos registros que `page_size`.

    Complexidade:
        - Tempo:   O(n) — percorre todos os registros uma vez.
        - Espaço:  O(n) — armazena todas as palavras nas páginas.

    Args:
        words:     Lista de palavras a serem distribuídas em páginas.
        page_size: Número máximo de registros por página. Deve ser >= 1.

    Returns:
        Lista de Page com todas as palavras organizadas sequencialmente.
        Exemplo com 5 palavras e page_size=2:
            Page(0, ["a","b"]), Page(1, ["c","d"]), Page(2, ["e"])

    Raises:
        ValueError: Se page_size < 1.

    Exemplo:
        >>> pages = build_pages(["a","b","c","d","e"], page_size=2)
        >>> len(pages)
        3
        >>> pages[0].records
        ['a', 'b']
        >>> pages[-1].records
        ['e']
    """
    if page_size < 1:
        raise ValueError(f"page_size deve ser >= 1, recebido: {page_size}")

    pages: list[Page] = []

    # range(0, n, step) produz os índices de início de cada página:
    # 0, page_size, 2*page_size, ...
    for i in range(0, len(words), page_size):
        chunk = words[i : i + page_size]   # fatia de no máximo page_size palavras
        page_id = i // page_size           # ID sequencial: 0, 1, 2, ...
        pages.append(Page(page_id=page_id, records=chunk))

    return pages
