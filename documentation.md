# Documentação — Índice Hash Estático

Este documento explica a arquitetura e o funcionamento de cada módulo do projeto de simulação de índice hash estático.

---

## Visão Geral

O projeto simula como um banco de dados real organiza e busca dados usando um **índice hash estático**. A ideia central é demonstrar a diferença de custo entre:

- **Busca por índice:** custo O(1) médio — aproximadamente 2 I/Os
- **Table Scan:** custo O(N) — até N/2 páginas lidas

Para 466 mil palavras com `PAGE_SIZE=100`, isso representa a diferença entre **2 leituras** e **~2.330 leituras** no caso médio.

---

## Arquitetura e Dependências

```
table_scan.py
     └── page.py

hash_index.py
     ├── page.py
     ├── bucket.py
     └── hash_function.py
```

Fluxo completo de uma busca por `"elephant"`:

```
1. hash_function("elephant", nb)  →  bucket_idx = 1042
2. Percorre Bucket[1042] (e overflows encadeados, se houver)
3. Encontra BucketEntry(key="elephant", page_id=312)
4. Lê Page[312]  →  retorna os records
```

---

## Módulos

### `core/page.py` — Unidade física de armazenamento

Em SGBDs reais, o disco lê dados em **blocos de tamanho fixo** chamados páginas. Quando o banco lê qualquer registro, ele lê a página inteira de uma vez — essa é a granularidade real de I/O. Este módulo simula esse comportamento.

#### `Page`

```python
@dataclass
class Page:
    page_id: int        # Identificador sequencial (0-indexed)
    records: list[str]  # Palavras armazenadas (máx. PAGE_SIZE)
```

O `page_id` é o que o índice armazena. Não a palavra em si, mas *onde ela está*.

#### `build_pages`

Divide uma lista de palavras em fatias de tamanho fixo:

```python
for i in range(0, len(words), page_size):
    chunk = words[i : i + page_size]
    page_id = i // page_size   # 0, 1, 2, ...
    pages.append(Page(page_id=page_id, records=chunk))
```

A última página pode ter menos registros — comportamento correto e esperado.

---

### `core/hash_function.py` — Algoritmo djb2

Implementa o hash **djb2**, criado por Dan Bernstein, adaptado para strings.

#### Como funciona

```python
h = 5381
for c in key:
    h = ((h << 5) + h) + ord(c)
return abs(h) % nb
```

| Etapa | Detalhe |
|---|---|
| `h = 5381` | Semente inicial — número primo com boa distribuição empírica |
| `(h << 5) + h` | Equivale a `h * 33`, mas via shift de bits (mais rápido em hardware) |
| `+ ord(c)` | Mistura o caractere atual no hash acumulado |
| `abs(h) % nb` | Garante resultado no intervalo `[0, nb)` sem índice negativo |

#### Propriedades garantidas

| Propriedade | Detalhe |
|---|---|
| **Determinismo** | Mesma chave → sempre mesmo bucket (essencial para o índice funcionar) |
| **Distribuição uniforme** | Palavras do inglês se distribuem bem entre os buckets |
| **Sensível à ordem** | `"abc"` e `"cba"` produzem buckets diferentes |
| **Custo** | O(\|key\|) — linear no tamanho da string |

> **Anti-padrão evitado:** usar `hash()` nativo do Python seria incorreto aqui porque o Python randomiza o seed a cada execução desde a versão 3.3 (proteção contra hash flooding — ver [PEP 456](https://peps.python.org/pep-0456/)). O djb2 garante o determinismo necessário.

---

### `core/bucket.py` — Estrutura do índice

Define as duas estruturas de dados que compõem o índice.

#### `BucketEntry`

```python
@dataclass
class BucketEntry:
    key: str      # A palavra indexada. Ex: "elephant"
    page_id: int  # Página onde "elephant" está armazenada
```

O "ponteiro" do índice: mapeia `"elephant" → Page 42`. Para recuperar o dado real, lemos `Page[42]`.

#### `Bucket`

```python
@dataclass
class Bucket:
    bucket_id: int
    entries: list[BucketEntry]   # máx. FR entradas
    overflow: Bucket | None = None  # lista ligada
```

A estratégia de resolução de colisões usada é **overflow chaining** — uma lista ligada de buckets. Quando um bucket primário está cheio, a inserção continua no próximo da cadeia:

```
Bucket[3]    → [e1, e2, e3]
    ↓ .overflow
Bucket[4700] → [e4, e5]
    ↓ .overflow
None
```

**Trade-off: Overflow Chaining vs. Open Addressing**

| Critério | Overflow Chaining | Open Addressing |
|---|---|---|
| Isolamento | Não contamina outros buckets primários | Pode causar clustering |
| Custo de busca | O(k), k = comprimento da cadeia | O(1) amortizado com fator de carga baixo |
| Memória | Ponteiros extras por bucket | Sem ponteiros, mas precisa de espaço livre |

---

### `core/hash_index.py` — Motor do índice

Núcleo do sistema: construção, busca e cálculo do número de buckets.

#### `calculate_nb`

```python
def calculate_nb(nr: int, fr: int) -> int:
    return math.ceil(nr / fr) + 1
```

O `+1` é sutil mas importante: se `NB == NR/FR` exatamente, os buckets ficam 100% cheios antes mesmo de qualquer colisão por hash — a probabilidade de overflow sobe muito. O `+1` garante folga mínima.

#### `build_index` — Algoritmo de construção

```
Para cada palavra em cada página:
  1. bucket_idx = hash_function(key, nb)
  2. Se Bucket[bucket_idx] está cheio → incrementa collision_count
  3. Caminha pela cadeia até achar espaço (criando overflow se necessário)
  4. Insere BucketEntry(key, page_id)
```

**Sobre as métricas coletadas:**

- `collision_count`: incrementado quando o bucket **primário** está cheio, independentemente de onde a chave será inserida. Mede a pressão sobre os buckets primários.
- `overflow_count`: conta quantos buckets de overflow foram criados. Indica fragmentação do índice.

**Complexidade:**

| Dimensão | Custo |
|---|---|
| Tempo | O(NR) — cada inserção é O(1) amortizado |
| Espaço | O(NR) — uma `BucketEntry` por registro |

#### `search_index` — Algoritmo de busca

```python
bucket_idx = hash_function(key, index.nb)
current = index.buckets[bucket_idx]

while current is not None:
    bucket_reads += 1
    for entry in current.entries:
        if entry.key == key:
            return entry  # encontrado
    current = current.overflow  # próximo na cadeia
```

**Custo de I/O:**

| Cenário | Custo |
|---|---|
| Melhor caso (sem overflow) | 2 I/Os: 1 bucket + 1 página |
| Com overflow (cadeia de k buckets) | k+1 I/Os |
| Chave inexistente | k I/Os (percorre toda a cadeia sem +1 de página) |

> A busca retorna apenas o `page_id`. A leitura efetiva da página de dados é contabilizada como +1 I/O na camada de apresentação.

---

### `core/table_scan.py` — Varredura sequencial

Implementa o **full table scan**: percorre todas as páginas em ordem sequencial até encontrar a chave ou esgotar todas as páginas.

```python
for page in pages:
    pages_read += 1          # 1 página lida = 1 I/O
    if key in page.records:
        return page.page_id  # encontrou — para imediatamente
```

O `in` faz busca linear na lista de records — O(PAGE_SIZE) por página.

**Quando o table scan é usado na prática:**

- Quando não existe índice para a coluna consultada
- Quando o otimizador estima que a seletividade é baixa (>~10–20% das linhas)
- Em tabelas muito pequenas (overhead do índice não compensa)

**Custo:**

| Caso | Páginas lidas |
|---|---|
| Melhor | 1 (chave na primeira página) |
| Médio | N/2 |
| Pior | N (chave na última página ou inexistente) |

---

## Comparativo final

Para `NR = 466.550 palavras`, `PAGE_SIZE = 100`, `FR = 10`:

| Método | I/Os médios | Complexidade |
|---|---|---|
| Busca por índice hash | ~2 | O(1) médio |
| Table Scan | ~2.330 | O(N) |

Isso demonstra quantitativamente por que índices são fundamentais em bancos de dados reais: uma busca que custaria mais de 2 mil leituras de disco passa a custar apenas 2.