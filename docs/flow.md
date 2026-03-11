# Fluxo Completo — Do Clique ao Core

---

## 1. "Carregar e Paginar"

```
Usuário clica "Carregar e Paginar"
        │
        ▼
LoadPanel._start_load()
  ├── desabilita botão
  ├── mostra progress bar
  └── cria e dispara LoadWorker (QThread)
              │
              ▼ (thread separada)
        LoadWorker.run()
          └── abre o arquivo .txt
                │
                ▼
              core/page.py → build_pages(words, page_size)
                │
                │  for i in range(0, len(words), page_size):
                │      chunk = words[i : i + page_size]
                │      page_id = i // page_size
                │      pages.append(Page(page_id=page_id, records=chunk))
                │
                │  Exemplo com 466.550 palavras e PAGE_SIZE=100:
                │  → Page(0,    ["aardvark", "abacus", ...])   # words[0:100]
                │  → Page(1,    ["bachelor", "badger", ...])   # words[100:200]
                │  → ...
                │  → Page(4665, ["zymurgy", ...])              # última, pode ter < 100
                │
                ▼
        finished.emit(words, pages)  →  volta para a thread principal
              │
              ▼
        LoadPanel._on_loaded()
          ├── exibe: "466.550 palavras | 4.666 páginas"
          ├── mostra preview da Page[0] e Page[4665]
          └── emite data_loaded(words, pages)
                    │
                    ▼
            MainWindow._on_data_loaded()
              ├── self._words = words
              ├── self._pages = pages
              ├── index_panel.set_pages(pages)  → habilita botão de construção
              ├── habilita Aba 2
              └── navega para Aba 2
```

---

## 2. "Construir Índice Hash"

```
Usuário ajusta FR=10 → NB é recalculado automaticamente
  └── core/hash_index.py → calculate_nb(466550, 10)
        └── math.ceil(466550 / 10) + 1 = 46.656 buckets

Usuário clica "Construir Índice Hash"
        │
        ▼
IndexPanel._start_build()
  └── cria e dispara IndexWorker(pages, nb=46656, fr=10)
              │
              ▼ (thread separada)
        IndexWorker.run()
          └── core/hash_index.py → build_index(pages, nb=46656, fr=10)
                │
                │  PASSO 1 — Inicializa os buckets primários
                │  buckets = [Bucket(id=0), Bucket(id=1), ..., Bucket(id=46655)]
                │  next_overflow_id = 46656
                │
                │  PASSO 2 — Percorre cada página e cada palavra
                │
                │  for page in pages:            # 4.666 páginas
                │    for key in page.records:    # até 100 palavras por página
                │
                │      ┌─────────────────────────────────────────────┐
                │      │  core/hash_function.py → hash_function(key, nb)
                │      │                                             │
                │      │  h = 5381                                   │
                │      │  for c in "elephant":                       │
                │      │      h = (h << 5) + h + ord(c)             │
                │      │  return abs(h) % 46656                      │
                │      │                                             │
                │      │  "elephant" → bucket_idx = 17.482          │
                │      └─────────────────────────────────────────────┘
                │
                │      primary = buckets[17482]
                │
                │      CASO A — bucket primário tem espaço (len < FR)
                │      ├── primary.is_full(10) → False
                │      └── primary.entries.append(
                │              BucketEntry(key="elephant", page_id=312)
                │          )
                │
                │      CASO B — bucket primário está cheio
                │      ├── primary.is_full(10) → True
                │      ├── collision_count += 1          ← registra colisão
                │      │
                │      │   caminha pela cadeia de overflow:
                │      │   current = primary
                │      │   while current.is_full(10):
                │      │       if current.overflow is None:
                │      │           current.overflow = Bucket(id=46656)
                │      │           overflow_count += 1   ← novo bucket criado
                │      │           next_overflow_id = 46657
                │      │       current = current.overflow
                │      │
                │      └── current.entries.append(BucketEntry(...))
                │
                ▼
        Resultado final (HashIndex):
          ├── buckets[0..46655]   — 46.656 buckets primários
          ├── nb = 46.656
          ├── fr = 10
          ├── collision_count = X  (inserções que bateram no primário cheio)
          └── overflow_count  = Y  (buckets de overflow criados)
                │
                ▼
        finished.emit(index, elapsed)  →  volta para thread principal
              │
              ▼
        IndexPanel._on_built()
          ├── exibe tempo, colisões, overflows
          └── emite index_built(index, elapsed)
                    │
                    ▼
            MainWindow._on_index_built()
              ├── search_panel.set_data(pages, index)
              ├── stats_panel.set_index(index, nr, elapsed)
              ├── habilita Abas 3 e 4
              └── navega para Aba 3
```

---

## 3. "Buscar Ambos"

```
Usuário digita "elephant" e clica "Buscar Ambos"
        │
        ▼
SearchPanel._do_both()
  ├── _do_index_search()
  └── _do_scan()
```

### Branch A — Busca por Índice

```
SearchPanel._do_index_search()
  │
  ▼
core/hash_index.py → search_index(index, "elephant")
  │
  │  PASSO 1 — descobre o bucket primário
  │  └── core/hash_function.py → hash_function("elephant", 46656)
  │        └── retorna 17.482
  │
  │  PASSO 2 — percorre a cadeia
  │  current = buckets[17482]
  │
  │  while current is not None:
  │      bucket_reads += 1            ← 1 I/O por bucket visitado
  │
  │      for entry in current.entries:
  │          if entry.key == "elephant":
  │              found_entry = entry  ← BucketEntry("elephant", page_id=312)
  │              break
  │
  │      if found_entry: break
  │      current = current.overflow   ← só entra aqui se não achou ainda
  │
  │  Cenário sem overflow:
  │  └── bucket_reads = 1, found = BucketEntry("elephant", 312)
  │
  │  Cenário com overflow (chave no 2° bucket):
  │  └── bucket_reads = 2, found = BucketEntry("elephant", 312)
  │
  ▼
retorna (entry, bucket_reads=1, elapsed)
  │
  ▼
SearchPanel atualiza widgets:
  ├── Bucket #17482  (laranja)       ← onde a hash mapeou
  ├── Página #312    (verde)         ← onde a palavra está
  ├── Custo: 2 I/Os  [1 bucket + 1 página]
  └── salva em _last_idx_result
```

### Branch B — Table Scan

```
SearchPanel._do_scan()
  │
  ▼
core/table_scan.py → table_scan(pages, "elephant")
  │
  │  for page in pages:       # percorre Page[0], Page[1], Page[2], ...
  │      pages_read += 1      ← 1 I/O por página
  │
  │      if "elephant" in page.records:   # busca linear dentro da página
  │          found_page_id = page.page_id
  │          break
  │
  │  "elephant" está na Page[312]:
  │  └── percorreu 313 páginas antes de encontrar (pages_read = 313)
  │
  ▼
retorna (page_id=312, pages_read=313, elapsed)
  │
  ▼
SearchPanel atualiza widgets:
  ├── Página #312  (azul)
  ├── Custo: 313 páginas lidas de 4.666 no total
  └── salva em _last_scan_result
```

### Comparativo — `_try_update_comparison()`

```
Ambos os resultados existem → monta a tabela:

  Palavra buscada: "elephant"
  ══════════════════════════════════════════════════════════
  Método                 Custo (I/Os)        Tempo
  ──────────────────────────────────────────────────────────
  Busca por Índice       2                   0.0021 ms
  Table Scan             313                 1.8400 ms
  ══════════════════════════════════════════════════════════
  Índice foi 876x mais rápido que o Table Scan.
  Diferença percentual de tempo: 99.89%
  Diferença de custo (I/Os): 313 (scan) vs 2 (índice)
```

---

## Conclusão

O ponto central que o fluxo deixa claro: o índice custa **sempre 2 I/Os** independente de onde a palavra estiver. O table scan custa **mais quanto mais tarde a palavra aparecer** — se "elephant" estivesse na última página, seriam 4.666 leituras contra os mesmos 2 do índice.

| Método | Melhor caso | Caso médio | Pior caso |
|---|---|---|---|
| Busca por Índice | 2 I/Os | 2 I/Os | k+1 I/Os (k = cadeia de overflow) |
| Table Scan | 1 página | N/2 páginas | N páginas |