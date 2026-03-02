# Índice Hash Estático

Trabalho acadêmico — Universidade de Fortaleza (UNIFOR)
Disciplina: Banco de Dados / Estruturas de Dados

> Aplicação desktop com GUI (PyQt6) que simula um **índice hash estático** sobre ~466 mil palavras em inglês, com busca por índice, table scan e comparação de desempenho.

---

## Índice

1. [O que é um Índice Hash?](#o-que-é-um-índice-hash)
2. [Pré-requisitos](#pré-requisitos)
3. [Instalação](#instalação)
4. [Como obter os dados](#como-obter-os-dados)
5. [Como executar](#como-executar)
6. [Guia de uso da interface](#guia-de-uso-da-interface)
7. [Arquitetura do projeto](#arquitetura-do-projeto)
8. [Algoritmos implementados](#algoritmos-implementados)
9. [Métricas e custo de I/O](#métricas-e-custo-de-io)
10. [Estrutura de diretórios](#estrutura-de-diretórios)

---

## O que é um Índice Hash?

Em bancos de dados, um **índice** é uma estrutura auxiliar que permite encontrar registros sem precisar varrer o arquivo inteiro. O índice hash é o mais rápido para buscas por igualdade (ex: "encontre a palavra 'apple'").

### Como funciona

```
Arquivo de dados (páginas):
  Página 0: [aardvark, aardwolf, ..., ablaze]
  Página 1: [able, abled, ..., abortive]
  ...
  Página 4665: [..., zymurgy]

Índice hash (NB buckets):
  Bucket[0]:    [(dog, pg12), (cat, pg3)]
  Bucket[1]:    [(apple, pg0), ...] → overflow → [...]
  Bucket[2]:    []
  ...
  Bucket[NB-1]: [(zoo, pg46)]
```

**Busca por índice** (custo fixo):
1. Calcula `idx = hash("apple") % NB` → O(1)
2. Lê `Bucket[idx]` → encontra `(apple, pg0)` → **1 leitura de bucket**
3. Lê `Página 0` → retorna a palavra → **1 leitura de página**
4. **Total: 2 I/Os** (independente do tamanho do arquivo!)

**Table scan** (custo variável):
1. Lê Página 0, Página 1, Página 2, ...
2. Verifica cada registro até encontrar
3. **Total: até 4.660 I/Os** no pior caso

---

## Pré-requisitos

- Python 3.11 ou superior
- [uv](https://docs.astral.sh/uv/) — gerenciador de pacotes e ambientes Python

### Instalar o uv

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Instalação

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd Projeto-indice-HASH

# 2. Instale as dependências (cria o virtualenv automaticamente)
uv sync
```

O `uv sync` lê o `pyproject.toml` e instala:
- `PyQt6` — biblioteca de GUI
- `pytest` (grupo dev) — para os testes unitários

---

## Como obter os dados

O arquivo `words_alpha.txt` **não está incluído** no repositório (é grande demais). Baixe-o separadamente:

```bash
# Opção 1: wget
wget https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt \
     -O data/words_alpha.txt

# Opção 2: curl
curl -L https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt \
     -o data/words_alpha.txt
```

O arquivo tem ~466.000 palavras em inglês, uma por linha, todas em minúsculas.

---

## Como executar

```bash
uv run main.py
```

Isso ativa o ambiente virtual gerenciado pelo `uv` e executa a aplicação.

---

## Guia de uso da interface

A interface é dividida em **4 abas** que devem ser usadas em ordem:

### Aba 1 — Carga de Dados

| Campo | Descrição |
|-------|-----------|
| **Selecionar Arquivo** | Navega até o arquivo `words_alpha.txt` |
| **PAGE_SIZE** | Número máximo de palavras por página (padrão: 100) |
| **Carregar e Paginar** | Lê o arquivo e cria as páginas (executa em background) |
| **Preview** | Exibe a primeira e a última página carregadas |

Após carregar, a **Aba 2** é habilitada automaticamente.

### Aba 2 — Índice Hash

| Campo | Descrição |
|-------|-----------|
| **FR** | Fator de Recarga: capacidade de cada bucket (padrão: 10) |
| **NB** | Número de buckets — calculado automaticamente: `⌈NR/FR⌉ + 1` |
| **Construir Índice Hash** | Inicia a construção em background (pode levar alguns segundos) |
| **Resultado** | Exibe tempo de construção, colisões e overflows |

Após construir, as **Abas 3 e 4** são habilitadas automaticamente.

### Aba 3 — Busca & Scan

Digite uma palavra e clique em:

- **Buscar por Índice** — usa o hash para localizar diretamente o bucket
  - Destaque **amarelo**: bucket acessado
  - Destaque **verde**: página onde a palavra está
- **Table Scan** — percorre todas as páginas sequencialmente
  - Destaque **azul**: página onde a palavra foi encontrada
- **Buscar Ambos** — executa os dois métodos e exibe a comparação

A tabela de comparação mostra custo (I/Os) e tempo para cada método.

### Aba 4 — Estatísticas

Exibe após a construção do índice:

- **Taxa de Colisão (%)**: proporção de inserções que encontraram o bucket primário cheio
- **Taxa de Overflow (%)**: proporção de buckets de overflow criados em relação a NB
- Detalhes completos: NR, NB, FR, contagens absolutas e tempo de construção

---

## Arquitetura do projeto

O projeto segue uma arquitetura em camadas com separação total entre lógica e UI:

```
┌─────────────────────────────────┐
│          ui/  (PyQt6)           │
│  main_window ← load_panel       │
│             ← index_panel       │
│             ← search_panel      │
│             ← stats_panel       │
├─────────────────────────────────┤
│          core/  (puro Python)   │
│  hash_function  page  bucket    │
│  hash_index     table_scan      │
└─────────────────────────────────┘
```

**Regra fundamental:** `core/` não importa nada de `ui/`. Isso garante que:
- A lógica pode ser testada sem iniciar a interface gráfica
- O código é mais fácil de explicar na apresentação
- Possível reutilizar o `core/` em outros projetos (web, CLI, etc.)

### Comunicação entre componentes

Os painéis se comunicam via **sinais Qt** (padrão Observer):

```
LoadPanel ──(data_loaded)──► MainWindow
  └─ passa words e pages para IndexPanel

IndexPanel ──(index_built)──► MainWindow
  └─ passa index para SearchPanel e StatsPanel
```

---

## Algoritmos implementados

### 1. Função Hash — djb2

```python
def hash_function(key: str, nb: int) -> int:
    h = 5381
    for c in key:
        h = ((h << 5) + h) + ord(c)   # h * 33 + ord(c)
    return abs(h) % nb
```

- **Autor original:** Dan Bernstein
- **Por que djb2?** Distribuição uniforme para strings ASCII, baixo número de colisões em vocabulários de idiomas naturais, implementação simples
- **Determinístico:** a mesma chave sempre produz o mesmo bucket (RNF05)
- **Complexidade:** O(|key|) — linear no tamanho da string

### 2. Divisão em Páginas

```python
def build_pages(words, page_size):
    pages = []
    for i in range(0, len(words), page_size):
        pages.append(Page(page_id=i // page_size, records=words[i:i+page_size]))
    return pages
```

Simula como um SGBD armazena registros em blocos de tamanho fixo no disco.

### 3. Construção do Índice — Overflow Chaining

```
Para cada palavra em cada página:
  1. idx ← hash(palavra) % NB
  2. Se Bucket[idx] está cheio:
       → registra COLISÃO
       → caminha para o bucket de overflow (criando se necessário)
  3. Insere BucketEntry(palavra, page_id) no bucket com espaço
```

A estrutura de overflow é uma **lista ligada de buckets**:

```
Bucket[i] → [e1, ..., e_FR] → Bucket[overflow1] → [e_FR+1, ...] → None
```

### 4. Busca por Índice

```
1. idx ← hash(chave) % NB                    → O(|chave|)
2. Percorre cadeia a partir de Bucket[idx]   → O(FR × cadeia)
3. Em cada bucket, compara entry.key == chave
4. Retorna BucketEntry ou None
```

### 5. Cálculo de NB

```python
nb = math.ceil(nr / fr) + 1
```

O `+1` garante que `NB > NR/FR`, evitando que todos os buckets fiquem completamente cheios desde o início, o que aumentaria as colisões.

---

## Métricas e custo de I/O

| Métrica | Fórmula | Significado |
|---------|---------|-------------|
| Taxa de Colisão | `(colisões / NR) × 100` | % de inserções que encontraram bucket primário cheio |
| Taxa de Overflow | `(overflows / NB) × 100` | % de buckets primários que criaram overflow |
| Custo — Índice | `leituras_bucket + 1` | I/Os para uma busca por índice |
| Custo — Scan | `páginas_lidas` | I/Os para o table scan |

### Comparação de desempenho (exemplo típico)

| Parâmetro | Valor |
|-----------|-------|
| NR | 466.550 palavras |
| PAGE_SIZE | 100 registros/página |
| Total de páginas | 4.666 |
| FR | 10 |
| NB | 46.656 buckets |

| Método | Custo médio | Custo pior caso |
|--------|-------------|-----------------|
| Busca por Índice | **2 I/Os** | 2–3 I/Os (com overflow) |
| Table Scan | **~2.333 I/Os** | 4.666 I/Os |

O índice é, em média, **~1.000x mais eficiente** que o table scan para este dataset.

---

## Estrutura de diretórios

```
Projeto-indice-HASH/
├── main.py                          # Entrypoint: uv run main.py
├── pyproject.toml                   # Dependências e configuração do projeto
├── CLAUDE.md                        # Especificação do trabalho
├── README.md                        # Este arquivo
│
├── data/
│   └── words_alpha.txt              # ~466k palavras (baixar separadamente)
│
├── core/                            # Lógica pura — zero dependência de UI
│   ├── __init__.py
│   ├── hash_function.py             # Algoritmo djb2
│   ├── page.py                      # Dataclass Page + build_pages()
│   ├── bucket.py                    # Dataclasses BucketEntry + Bucket
│   ├── hash_index.py                # HashIndex + build_index() + search_index()
│   └── table_scan.py                # table_scan() com contagem de I/Os
│
└── ui/                              # Interface gráfica PyQt6
    ├── __init__.py
    ├── main_window.py               # QMainWindow + QTabWidget + estado global
    └── panels/
        ├── __init__.py
        ├── load_panel.py            # Aba 1: carga de arquivo (HU01-03)
        ├── index_panel.py           # Aba 2: construção do índice (HU04-08)
        ├── search_panel.py          # Aba 3: busca + scan + comparação (HU09-11, 14)
        └── stats_panel.py           # Aba 4: taxas de colisão e overflow (HU12-13)
```

---

## Critérios de Avaliação Atendidos

| Critério | Implementação |
|----------|--------------|
| Interface gráfica funcional | PyQt6 com 4 abas |
| Carga de dados nas páginas | `LoadPanel` + `build_pages()` em QThread |
| Entrada para tamanho da página | `QSpinBox` PAGE_SIZE (Aba 1) |
| Cálculo da quantidade de páginas | `len(pages)` exibido após carga |
| Construção e uso da função hash | `hash_function.py` com djb2 |
| Cálculo da quantidade de buckets | `calculate_nb()` — `⌈NR/FR⌉ + 1` |
| Pesquisa com uso do índice | `search_index()` + highlight visual |
| Taxa de colisões | `StatsPanel` — card com barra |
| Taxa de overflow | `StatsPanel` — card com barra |
| Table Scan | `table_scan()` com contagem de páginas |
| Custo + comparativo de tempo | Tabela na Aba 3 (custo I/Os + ms) |
