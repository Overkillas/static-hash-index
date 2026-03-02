"""
Módulo: core/hash_index.py
===========================
Núcleo do índice hash estático: construção, busca e cálculo de NB.

Visão geral do índice hash estático:
--------------------------------------
Um índice hash mapeia cada chave (palavra) diretamente a um bucket usando
uma função hash. Isso permite busca em tempo O(1) no caso médio — muito mais
eficiente que um table scan O(n).

Estrutura do índice:
----------------------
  ┌──────────────────────────────────────────────────────────┐
  │  Índice Hash (NB buckets)                                │
  │                                                          │
  │  Bucket[0]: [(apple,pg2), (zoo,pg10)]                    │
  │  Bucket[1]: [(hello,pg0), (world,pg1)] → [overflow...]   │
  │  Bucket[2]: []                                           │
  │  ...                                                     │
  │  Bucket[NB-1]: [(python,pg45)]                           │
  └──────────────────────────────────────────────────────────┘

Algoritmo de inserção:
------------------------
  1. Calcular idx = hash_function(key, nb)
  2. Verificar se Bucket[idx] está cheio:
     - Se SIM → registrar COLISÃO, caminhar para overflow
     - Se NÃO → inserir diretamente
  3. Na cadeia de overflow, encontrar um bucket com espaço
     (criando novos buckets de overflow quando necessário)
  4. Inserir BucketEntry(key, page_id) no bucket encontrado

Algoritmo de busca:
-------------------
  1. Calcular idx = hash_function(key, nb)
  2. Percorrer a cadeia a partir de Bucket[idx]
  3. Em cada bucket, verificar se alguma entrada tem entry.key == key
  4. Retornar a entrada encontrada (ou None)
  Custo: 1 a k leituras de bucket (k = comprimento da cadeia), + 1 página.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from core.bucket import Bucket, BucketEntry
from core.hash_function import hash_function
from core.page import Page


@dataclass
class HashIndex:
    """
    Representa o índice hash estático completo.

    Attributes:
        buckets:         Lista de NB buckets primários (índice).
        nb:              Número de buckets primários.
        fr:              Fator de Recarga — capacidade máxima de cada bucket.
        collision_count: Quantas inserções encontraram o bucket primário cheio.
                         Métrica: taxa_colisão = (collision_count / NR) * 100
        overflow_count:  Quantos buckets de overflow foram criados durante a
                         construção do índice.
                         Métrica: taxa_overflow = (overflow_count / NB) * 100
    """

    buckets: list[Bucket]
    nb: int
    fr: int
    collision_count: int = 0
    overflow_count: int = 0


def calculate_nb(nr: int, fr: int) -> int:
    """
    Calcula o número ideal de buckets primários (NB).

    Fórmula: NB = ⌈NR / FR⌉ + 1

    O +1 garante que NB > NR/FR, evitando que todos os buckets fiquem
    exatamente cheios (o que aumentaria a probabilidade de colisões).

    Args:
        nr: Número total de registros (palavras no arquivo).
        fr: Fator de Recarga (entradas por bucket).

    Returns:
        Número de buckets recomendado.

    Exemplo:
        >>> calculate_nb(466_550, 10)
        46_656   # = ceil(466550/10) + 1 = 46655 + 1
    """
    return math.ceil(nr / fr) + 1


def build_index(pages: list[Page], nb: int, fr: int) -> tuple[HashIndex, float]:
    """
    Constrói o índice hash percorrendo todas as páginas de dados.

    Para cada palavra em cada página, insere uma entrada no bucket calculado
    pela função hash. Resolve colisões via overflow chaining.

    Detalhes do algoritmo:
        - Inicializa NB buckets primários vazios (IDs 0 a NB-1).
        - Para cada (key, page_id), calcula idx = hash_function(key, nb).
        - Se Bucket[idx] está cheio → incrementa collision_count.
        - Caminha pela cadeia de overflow até encontrar espaço.
        - Se precisar criar novo bucket de overflow → incrementa overflow_count.
        - Insere BucketEntry(key, page_id).

    Complexidade:
        - Tempo:  O(NR) no caso médio — cada inserção é O(1) amortizado.
        - Espaço: O(NR) — uma BucketEntry por registro.

    Args:
        pages: Lista de páginas com as palavras a indexar.
        nb:    Número de buckets primários.
        fr:    Fator de Recarga (capacidade por bucket).

    Returns:
        Tupla (HashIndex, tempo_em_segundos_float).
    """
    # Cria os NB buckets primários com IDs de 0 a nb-1
    buckets: list[Bucket] = [Bucket(bucket_id=i) for i in range(nb)]

    collision_count = 0
    overflow_count = 0

    # Contador para gerar IDs únicos para buckets de overflow (>= nb)
    next_overflow_id = nb

    t_start = time.perf_counter()

    for page in pages:
        for key in page.records:
            # Passo 1: Descobre qual bucket primário deve receber esta chave
            bucket_idx = hash_function(key, nb)
            primary_bucket = buckets[bucket_idx]

            # Passo 2: Verifica se o bucket primário está cheio → colisão
            # Colisão = inserção que ENCONTRA o bucket primário já cheio.
            # Não importa se a chave acabará em um overflow — a colisão
            # é contabilizada assim que o primário está cheio.
            if primary_bucket.is_full(fr):
                collision_count += 1

            # Passo 3: Caminha pela cadeia de overflow até encontrar espaço
            current = primary_bucket
            while current.is_full(fr):
                if current.overflow is None:
                    # Cria novo bucket de overflow (contabiliza overflow)
                    current.overflow = Bucket(bucket_id=next_overflow_id)
                    next_overflow_id += 1
                    overflow_count += 1
                current = current.overflow

            # Passo 4: Insere a entrada no bucket com espaço disponível
            current.entries.append(BucketEntry(key=key, page_id=page.page_id))

    t_end = time.perf_counter()
    elapsed = t_end - t_start

    index = HashIndex(
        buckets=buckets,
        nb=nb,
        fr=fr,
        collision_count=collision_count,
        overflow_count=overflow_count,
    )
    return index, elapsed


def search_index(
    index: HashIndex, key: str
) -> tuple[BucketEntry | None, int, float]:
    """
    Busca uma chave no índice hash.

    Algoritmo de busca:
        1. Calcula idx = hash_function(key, index.nb)  → O(|key|)
        2. Percorre a cadeia de buckets a partir de Bucket[idx]
        3. Em cada bucket, procura entry.key == key     → O(FR) por bucket
        4. Retorna a entrada encontrada ou None

    Custo de I/O:
        - Leituras de bucket: 1 a k (k = buckets percorridos na cadeia)
        - Leitura de página:  1 (se a chave foi encontrada)
        - Total mínimo:  2 I/Os  (1 bucket + 1 página, no melhor caso)
        - Total máximo: k+1 I/Os (chave no último overflow)

    Nota: A busca NÃO lê a página de dados — ela apenas retorna o page_id.
    O custo de leitura de página (+1) é calculado na camada de UI.

    Args:
        index: O índice hash já construído.
        key:   Palavra a ser buscada (deve estar em minúsculas).

    Returns:
        Tupla (BucketEntry | None, bucket_reads, tempo_em_segundos).
        - BucketEntry: a entrada encontrada (ou None se não existir).
        - bucket_reads: quantos buckets foram lidos (custo de I/O de índice).
        - tempo: tempo de execução medido com time.perf_counter().
    """
    t_start = time.perf_counter()

    # Calcula o bucket primário onde a chave deveria estar
    bucket_idx = hash_function(key, index.nb)
    current: Bucket | None = index.buckets[bucket_idx]

    bucket_reads = 0
    found_entry: BucketEntry | None = None

    # Percorre a cadeia de buckets (primário + overflows)
    while current is not None:
        bucket_reads += 1  # cada bucket visitado = 1 leitura de I/O

        # Busca linear dentro do bucket (máximo FR entradas)
        for entry in current.entries:
            if entry.key == key:
                found_entry = entry
                break

        if found_entry is not None:
            break  # encontrou — não precisa verificar overflow

        current = current.overflow  # passa para o próximo bucket na cadeia

    t_end = time.perf_counter()
    elapsed = t_end - t_start

    return found_entry, bucket_reads, elapsed
