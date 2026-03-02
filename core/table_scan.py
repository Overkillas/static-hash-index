"""
Módulo: core/table_scan.py
===========================
Implementa a varredura sequencial (table scan) das páginas de dados.

O que é um table scan?
-----------------------
Um table scan (ou full table scan) é o método mais simples de busca em um
banco de dados: percorrer TODAS as páginas, uma a uma, verificando cada
registro até encontrar o dado desejado (ou concluir que ele não existe).

Quando não há índice disponível, o banco de dados recorre ao table scan.
É a estratégia de "força bruta" de leitura.

Custo do table scan:
---------------------
- Melhor caso:  1 página lida  (a chave está na primeira página)
- Pior caso:    N páginas lidas (chave na última página ou inexistente)
- Caso médio:   N/2 páginas lidas (chave em posição aleatória)

Comparação com busca por índice:
----------------------------------
  | Método          | Custo médio (I/Os) | Complexidade |
  |-----------------|-------------------|--------------|
  | Busca por Índice| 2 (bucket + pág.) | O(1) médio   |
  | Table Scan      | N/2               | O(N)         |

Para N = 4.660 páginas (466k palavras, PAGE_SIZE=100):
  - Índice:     2 I/Os
  - Table Scan: ~2.330 I/Os em média

Isso demonstra a importância de índices em bancos de dados reais.
"""

from __future__ import annotations

import time

from core.page import Page


def table_scan(pages: list[Page], key: str) -> tuple[int | None, int, float]:
    """
    Realiza uma varredura sequencial das páginas para encontrar uma chave.

    Percorre as páginas em ordem crescente de page_id. Para cada página,
    verifica se `key` está na lista `records`. Para assim que encontra.

    Cada página percorrida conta como 1 leitura de I/O, independentemente
    de quantos registros ela contém (em um SGBD real, a granularidade de
    leitura é a página — não o registro individual).

    Complexidade:
        - Tempo:   O(NR) no pior caso — percorre todos os registros.
        - Espaço:  O(1) — não usa memória adicional proporcional a NR.

    Args:
        pages: Lista de páginas a percorrer (em ordem de page_id).
        key:   Palavra a ser encontrada (deve estar em minúsculas).

    Returns:
        Tupla (page_id | None, pages_read, tempo_em_segundos):
        - page_id:     ID da página onde a chave foi encontrada.
                       None se a chave não existe em nenhuma página.
        - pages_read:  Número de páginas lidas até encontrar (ou total se
                       não encontrou). Este é o "custo" do table scan.
        - tempo:       Tempo de execução em segundos (time.perf_counter).

    Exemplo:
        >>> # Supondo que "apple" está na página 0
        >>> page_id, cost, time_s = table_scan(pages, "apple")
        >>> page_id
        0
        >>> cost
        1   # encontrou na primeira página — só 1 leitura
    """
    t_start = time.perf_counter()

    pages_read = 0
    found_page_id: int | None = None

    for page in pages:
        # Cada página percorrida = 1 leitura de I/O
        pages_read += 1

        # Verifica se a chave existe entre os registros desta página.
        # `in` faz busca linear na lista — O(PAGE_SIZE) por página.
        if key in page.records:
            found_page_id = page.page_id
            break  # encontrou — para imediatamente (não lê páginas seguintes)

    t_end = time.perf_counter()
    elapsed = t_end - t_start

    return found_page_id, pages_read, elapsed
