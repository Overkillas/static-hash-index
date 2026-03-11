# Projeto 1 — Índice Hash Estático

Trabalho acadêmico (30% da nota) — Universidade de Fortaleza
Disciplina: Banco de Dados / Estruturas de Dados
Equipe: até 4 pessoas

---

## Objetivo

Implementar uma aplicação com **GUI** que simula um índice hash estático sobre ~466k palavras em inglês.
Fonte dos dados: https://github.com/dwyl/english-words (arquivo `words_alpha.txt`)

---

## Stack Definida

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Gerenciador | uv |
| GUI | PyQt6 |
| Testes | pytest |

---

## Estrutura de Diretórios

```
hash-index/
├── CLAUDE.md
├── pyproject.toml
├── data/
│   └── words_alpha.txt          # ~466k palavras, uma por linha
├── core/                        # Lógica pura — zero dependência de UI
│   ├── __init__.py
│   ├── page.py                  # Estrutura Page + divisão de registros
│   ├── bucket.py                # Estrutura Bucket + overflow chaining
│   ├── hash_function.py         # Função hash djb2
│   ├── hash_index.py            # Construção e busca do índice
│   └── table_scan.py            # Table scan com métricas
├── ui/
│   ├── __init__.py
│   ├── main_window.py           # QMainWindow principal com abas
│   └── panels/
│       ├── load_panel.py        # Carga do arquivo + visualização de páginas
│       ├── index_panel.py       # Construção do índice + parâmetros NB/FR
│       ├── search_panel.py      # Busca por índice + table scan + comparação
│       └── stats_panel.py       # Métricas: colisões, overflow, custo, tempo
└── main.py                      # Entrypoint: `uv run main.py`
```

---

## Estruturas de Dados

```python
# core/page.py
@dataclass
class Page:
    page_id: int
    records: list[str]   # até PAGE_SIZE palavras

# core/bucket.py
@dataclass
class BucketEntry:
    key: str
    page_id: int

@dataclass
class Bucket:
    bucket_id: int
    entries: list[BucketEntry]  # capacidade máxima = FR
    overflow: 'Bucket | None'   # encadeamento de overflow

# core/hash_index.py
@dataclass
class HashIndex:
    buckets: list[Bucket]
    nb: int               # número de buckets
    fr: int               # capacidade por bucket
    collision_count: int  # inserções que encontraram bucket cheio
    overflow_count: int   # buckets que criaram overflow
```

---

## Algoritmos Definidos

### Função Hash — djb2 adaptada para strings
```python
def hash_function(key: str, nb: int) -> int:
    h = 5381
    for c in key:
        h = ((h << 5) + h) + ord(c)  # h * 33 + c
    return abs(h) % nb
```
- Determinística: mesma chave → mesmo bucket (RNF05)
- Boa distribuição para strings em inglês

### Resolução de Colisão → Overflow Chaining
Quando um bucket atinge FR, cria-se um novo bucket encadeado:
```
Bucket[i] → [e1, e2, ..., e_FR] → overflow_bucket → overflow_bucket → None
```
- Colisão é contabilizada quando a inserção encontra o bucket primário cheio
- Overflow é contabilizado quando um novo bucket encadeado é criado
- Simples de visualizar na UI com setas/ligações entre buckets

### Cálculo de NB
```python
import math
nb = math.ceil(nr / fr) + 1   # garante NB > NR/FR (RN08)
```

---

## Métricas

| Métrica | Cálculo |
|---|---|
| Taxa de colisão (%) | `(collision_count / NR) * 100` |
| Taxa de overflow (%) | `(overflow_count / NB) * 100` |
| Custo busca por índice | `1 (leitura bucket) + 1 (leitura página) = 2` |
| Custo table scan | número real de páginas lidas até encontrar a chave |
| Tempo | `time.perf_counter()` antes e depois de cada operação |

---

## Histórias de Usuário (Referência Rápida)

| HU | Epic | Resumo |
|---|---|---|
| HU01 | Carga | Carregar arquivo .txt |
| HU02 | Carga | Definir PAGE_SIZE via interface |
| HU03 | Carga | Dividir registros em páginas; mostrar 1ª e última página |
| HU04 | Índice | Criar NB buckets de capacidade FR |
| HU05 | Índice | Implementar função hash configurável |
| HU06 | Índice | Construir índice percorrendo páginas |
| HU07 | Colisão | Resolver colisões (overflow chaining) |
| HU08 | Overflow | Tratar bucket overflow |
| HU09 | Busca | Busca por índice → mostra página + custo |
| HU10 | Scan | Table scan → mostra páginas lidas + custo |
| HU11 | Scan | Comparar tempo e custo índice vs scan |
| HU12 | Stats | Taxa de colisões (%) |
| HU13 | Stats | Taxa de overflow (%) |
| HU14 | UI | GUI com highlight de bucket e página durante busca |

---

## Critérios de Avaliação

| Critério | Nota |
|---|---|
| Interface gráfica (funcional) | 1,0 |
| Carga de dados nas páginas (funcional + código) | 1,5 |
| Entrada para tamanho da página (funcional + código) | 1,0 |
| Cálculo da quantidade de páginas (funcional + código) | 1,0 |
| Construção e uso da função hash (funcional + código) | 1,0 |
| Cálculo da quantidade de buckets (funcional + código) | 0,5 |
| Pesquisa com uso do índice (funcional + código) | 2,0 |
| Taxa de colisões (funcional) | 0,5 |
| Taxa de overflow (funcional) | 0,5 |
| Table Scan (funcional) | 0,5 |
| Estimativa de custo + comparativo de tempo (funcional) | 0,5 |
| **Total** | **10,0** |

---

## Requisitos Não Funcionais

- **RNF01**: suportar 466.000+ registros sem travar
- **RNF02**: exibir tempo de construção do índice
- **RNF03**: qualquer linguagem — usamos Python
- **RNF04**: interface visual (desktop ou web) — sem terminal/popup
- **RNF05**: determinístico — mesma chave → mesmo bucket sempre

---

## Ordem de Implementação Recomendada

```
[1] core/hash_function.py      — função djb2, testes unitários
[2] core/page.py               — dataclass Page, divisão de registros
[3] core/bucket.py             — dataclass Bucket + overflow chaining
[4] core/hash_index.py         — construção completa do índice
[5] core/table_scan.py         — varredura sequencial com contagem de páginas
[6] ui/main_window.py          — esqueleto com abas (QTabWidget)
[7] ui/panels/load_panel.py    — carga de arquivo + visualização 1ª/última página
[8] ui/panels/index_panel.py   — inputs NB/FR + botão construir + tempo
[9] ui/panels/search_panel.py  — busca + scan + highlight + comparação
[10] ui/panels/stats_panel.py  — taxas de colisão e overflow
```

---

## Parâmetros Sugeridos (Defaults)

| Parâmetro | Valor sugerido | Motivo |
|---|---|---|
| PAGE_SIZE | 100 registros/página | ~4.660 páginas para 466k palavras |
| FR | 10 entradas/bucket | Bom equilíbrio colisão/memória |
| NB | `ceil(NR / FR) + 1` | Garante NB > NR/FR |

---

## Notas Importantes

- O módulo `core/` deve ser 100% independente de UI — facilita testes e explicação do código na apresentação
- Usar `time.perf_counter()` para medir tempo (mais preciso que `time.time()`)
- Durante a busca visual (CA29), emitir sinais Qt para destacar o bucket e a página acessados
- O arquivo `words_alpha.txt` deve ser baixado separadamente (não comitar no repo)
- Colisão só é contabilizada quando o bucket primário está cheio (RN14)
