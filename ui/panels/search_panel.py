"""
Módulo: ui/panels/search_panel.py
===================================
Painel de busca e comparação — Aba 3 da interface.

Responsabilidades (HU09, HU10, HU11, HU14):
  - HU09: Busca por índice → mostra bucket acessado, página encontrada e custo.
  - HU10: Table scan → mostra páginas lidas e custo.
  - HU11: Comparar tempo e custo índice vs table scan.
  - HU14: Destacar visualmente o bucket e a página acessados.

Fluxo de uso:
  1. Usuário digita uma palavra no campo de busca.
  2. Clica em "Buscar por Índice", "Table Scan" ou "Buscar Ambos".
  3. Os resultados aparecem nos painéis laterais com destaque colorido.
  4. A tabela de comparação mostra custo e tempo lado a lado.

Custo de I/O:
  - Busca por índice: N leituras de bucket + 1 leitura de página
    (N = tamanho da cadeia de overflow percorrida, geralmente N=1)
  - Table scan: K leituras de página até encontrar a chave
    (K = posição da palavra na sequência de páginas)

Destaque visual (HU14):
  - Bucket acessado: fundo laranja escuro + texto branco
  - Página encontrada (índice): fundo verde escuro + texto branco
  - Página encontrada (scan): fundo azul marinho + texto branco
  - Não encontrado: fundo vermelho escuro + texto branco
  - Inativo: fundo cinza claro + texto cinza escuro
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QFormLayout,
)

from core.hash_function import hash_function
from core.hash_index import HashIndex, search_index
from core.page import Page
from core.table_scan import table_scan as do_table_scan


# ---------------------------------------------------------------------------
# Widget auxiliar: Label com destaque colorido
# ---------------------------------------------------------------------------

class HighlightLabel(QLabel):
    """
    QLabel com fundo colorido para destacar resultados de busca.

    Cada estado usa um par (fundo, texto, borda) com contraste garantido.
    Nunca deixamos o Qt escolher a cor do texto — isso evitava o branco
    sobre amarelo claro que tornava a leitura impossível.

    Estados:
    - BUCKET: fundo âmbar escuro + texto branco (bucket acessado)
    - INDEX:  fundo verde escuro + texto branco (página via índice)
    - SCAN:   fundo azul escuro  + texto branco (página via scan)
    - ERROR:  fundo vermelho     + texto branco (não encontrado)
    - OFF:    fundo cinza claro  + texto cinza escuro (inativo)
    """

    # Tuplas (bg, text_color, border_color) — contraste WCAG AA garantido
    STYLE_BUCKET = ("#E65100", "#FFFFFF", "#BF360C")   # laranja escuro / branco
    STYLE_INDEX  = ("#1B5E20", "#FFFFFF", "#004D00")   # verde floresta / branco
    STYLE_SCAN   = ("#0D47A1", "#FFFFFF", "#002171")   # azul marinho   / branco
    STYLE_ERROR  = ("#B71C1C", "#FFFFFF", "#7F0000")   # vermelho escuro / branco
    STYLE_OFF    = ("#EEEEEE", "#424242", "#BDBDBD")   # cinza claro / cinza escuro

    def __init__(self, text: str = "", active_style: tuple = STYLE_BUCKET) -> None:
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._active_style = active_style
        self._apply_style(*self.STYLE_OFF)

    def activate(self, text: str) -> None:
        """Ativa o destaque colorido e exibe o texto."""
        self.setText(text)
        self._apply_style(*self._active_style)

    def deactivate(self, text: str = "—") -> None:
        """Volta ao estado inativo (cinza neutro)."""
        self.setText(text)
        self._apply_style(*self.STYLE_OFF)

    def set_error(self, text: str) -> None:
        """Destaque vermelho para indicar 'não encontrado'."""
        self.setText(text)
        self._apply_style(*self.STYLE_ERROR)

    def _apply_style(self, bg: str, fg: str, border: str) -> None:
        """Aplica fundo, cor de texto e borda explicitamente."""
        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 2px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 13px;
            }}
            """
        )


# ---------------------------------------------------------------------------
# Painel principal
# ---------------------------------------------------------------------------

class SearchPanel(QWidget):
    """
    Painel de busca e comparação — Aba 3.

    Não emite sinais — todos os resultados são exibidos internamente.
    """

    def __init__(self) -> None:
        super().__init__()
        self._pages: list[Page] = []
        self._index: HashIndex | None = None

        # Armazena os últimos resultados para o comparativo
        self._last_idx_result: tuple | None = None   # (entry, bucket_reads, elapsed)
        self._last_scan_result: tuple | None = None  # (page_id, pages_read, elapsed)

        self._setup_ui()

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Campo de busca e botões ───────────────────────────────────
        search_group = QGroupBox("Palavra a Buscar")
        search_layout = QHBoxLayout(search_group)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Digite uma palavra em inglês... (ex: apple)")
        self.search_input.setToolTip("A busca é case-insensitive (convertida para minúsculas)")
        self.search_input.returnPressed.connect(self._do_both)
        search_layout.addWidget(self.search_input, stretch=1)

        self.idx_btn = QPushButton("Buscar por Indice")
        self.idx_btn.setEnabled(False)
        self.idx_btn.setToolTip("Usa o índice hash: O(1) médio")
        self.idx_btn.clicked.connect(self._do_index_search)
        search_layout.addWidget(self.idx_btn)

        self.scan_btn = QPushButton("Table Scan")
        self.scan_btn.setEnabled(False)
        self.scan_btn.setToolTip("Varredura sequencial: O(N) no pior caso")
        self.scan_btn.clicked.connect(self._do_scan)
        search_layout.addWidget(self.scan_btn)

        self.both_btn = QPushButton("Buscar Ambos")
        self.both_btn.setEnabled(False)
        self.both_btn.setToolTip("Executa índice + scan e exibe o comparativo")
        self.both_btn.clicked.connect(self._do_both)
        search_layout.addWidget(self.both_btn)

        layout.addWidget(search_group)

        # ── Resultados lado a lado ────────────────────────────────────
        results_layout = QHBoxLayout()

        # Resultado — Busca por Índice
        idx_group = QGroupBox("Busca por Indice (Hash)")
        idx_form = QFormLayout(idx_group)
        idx_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.idx_status_label = QLabel("—")
        idx_form.addRow("Status:", self.idx_status_label)

        self.idx_bucket_hl = HighlightLabel(
            active_style=HighlightLabel.STYLE_BUCKET
        )
        idx_form.addRow("Bucket Acessado:", self.idx_bucket_hl)

        self.idx_chain_label = QLabel("—")
        self.idx_chain_label.setWordWrap(True)
        idx_form.addRow("Cadeia de Overflow:", self.idx_chain_label)

        self.idx_page_hl = HighlightLabel(
            active_style=HighlightLabel.STYLE_INDEX
        )
        idx_form.addRow("Pagina Encontrada:", self.idx_page_hl)

        self.idx_cost_label = QLabel("—")
        idx_form.addRow("Custo (I/Os):", self.idx_cost_label)

        self.idx_time_label = QLabel("—")
        idx_form.addRow("Tempo:", self.idx_time_label)

        results_layout.addWidget(idx_group)

        # Resultado — Table Scan
        scan_group = QGroupBox("Table Scan (Varredura Sequencial)")
        scan_form = QFormLayout(scan_group)
        scan_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.scan_status_label = QLabel("—")
        scan_form.addRow("Status:", self.scan_status_label)

        self.scan_page_hl = HighlightLabel(
            active_style=HighlightLabel.STYLE_SCAN
        )
        scan_form.addRow("Pagina Encontrada:", self.scan_page_hl)

        self.scan_cost_label = QLabel("—")
        scan_form.addRow("Custo (paginas lidas):", self.scan_cost_label)

        self.scan_time_label = QLabel("—")
        scan_form.addRow("Tempo:", self.scan_time_label)

        results_layout.addWidget(scan_group)
        layout.addLayout(results_layout)

        # ── Tabela de comparação ──────────────────────────────────────
        cmp_group = QGroupBox("Comparativo: Indice vs Table Scan")
        cmp_layout = QVBoxLayout(cmp_group)

        self.comparison_text = QTextEdit()
        self.comparison_text.setReadOnly(True)
        self.comparison_text.setMaximumHeight(130)
        self.comparison_text.setFont(self.comparison_text.font())
        self.comparison_text.setPlaceholderText(
            "Execute 'Buscar Ambos' para ver a comparação de custo e tempo."
        )
        cmp_layout.addWidget(self.comparison_text)

        layout.addWidget(cmp_group)
        layout.addStretch()

    # ------------------------------------------------------------------
    # Interface pública (chamada pela MainWindow)
    # ------------------------------------------------------------------

    def set_data(self, pages: list[Page], index: HashIndex) -> None:
        """
        Recebe as páginas e o índice construído, e habilita os botões.

        Args:
            pages: Lista de páginas para o table scan.
            index: O índice hash para a busca direta.
        """
        self._pages = pages
        self._index = index
        self.idx_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.both_btn.setEnabled(True)
        # Limpa resultados anteriores (caso o índice tenha sido reconstruído)
        self._clear_results()

    # ------------------------------------------------------------------
    # Handlers de busca
    # ------------------------------------------------------------------

    def _do_index_search(self) -> None:
        """Executa a busca usando o índice hash e atualiza os widgets."""
        if self._index is None:
            return

        key = self.search_input.text().strip().lower()
        if not key:
            return

        entry, bucket_reads, elapsed = search_index(self._index, key)

        # Calcula o bucket primário que seria acessado
        primary_id = hash_function(key, self._index.nb)
        primary_bucket = self._index.buckets[primary_id]

        if entry is not None:
            self.idx_status_label.setText(
                f'Encontrada: "{key}"'
            )
            self.idx_status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")

            # Destaque amarelo no bucket
            self.idx_bucket_hl.activate(
                f"Bucket #{primary_id}  ({bucket_reads} leitura(s))"
            )

            # Mostra cadeia de overflow textualmente
            chain_str = primary_bucket.get_chain_summary()
            # Limita a exibição para não ocupar muito espaço
            if len(chain_str) > 120:
                chain_str = chain_str[:120] + "..."
            self.idx_chain_label.setText(chain_str)

            # Destaque verde na página
            self.idx_page_hl.activate(f"Pagina #{entry.page_id}")

            # Custo total = leituras de bucket + 1 leitura de página
            total_cost = bucket_reads + 1
            self.idx_cost_label.setText(
                f"{total_cost} I/O(s)  [{bucket_reads} bucket(s) + 1 pagina]"
            )

        else:
            self.idx_status_label.setText(f'Nao encontrada: "{key}"')
            self.idx_status_label.setStyleSheet("color: #C62828; font-weight: bold;")
            self.idx_bucket_hl.set_error(f"Bucket #{primary_id}  (verificado)")
            self.idx_chain_label.setText(primary_bucket.get_chain_summary()[:120])
            self.idx_page_hl.deactivate("Nao encontrada")
            total_cost = bucket_reads
            self.idx_cost_label.setText(
                f"{total_cost} bucket(s) lido(s) — nao encontrada"
            )

        self.idx_time_label.setText(f"{elapsed * 1_000:.4f} ms")
        self._last_idx_result = (entry, bucket_reads, elapsed)
        self._try_update_comparison()

    def _do_scan(self) -> None:
        """Executa o table scan sequencial e atualiza os widgets."""
        if not self._pages:
            return

        key = self.search_input.text().strip().lower()
        if not key:
            return

        page_id, pages_read, elapsed = do_table_scan(self._pages, key)

        if page_id is not None:
            self.scan_status_label.setText(f'Encontrada: "{key}"')
            self.scan_status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
            # Destaque azul na página
            self.scan_page_hl.activate(f"Pagina #{page_id}")
        else:
            self.scan_status_label.setText(f'Nao encontrada: "{key}"')
            self.scan_status_label.setStyleSheet("color: #C62828; font-weight: bold;")
            self.scan_page_hl.set_error("Nao encontrada")

        self.scan_cost_label.setText(
            f"{pages_read:,} pagina(s) lida(s)  "
            f"de {len(self._pages):,} no total"
        )
        self.scan_time_label.setText(f"{elapsed * 1_000:.4f} ms")

        self._last_scan_result = (page_id, pages_read, elapsed)
        self._try_update_comparison()

    def _do_both(self) -> None:
        """Executa índice e scan em sequência, depois exibe o comparativo."""
        key = self.search_input.text().strip().lower()
        if not key:
            return
        self._do_index_search()
        self._do_scan()

    # ------------------------------------------------------------------
    # Comparativo
    # ------------------------------------------------------------------

    def _try_update_comparison(self) -> None:
        """Atualiza a tabela comparativa se ambos os resultados existem."""
        if self._last_idx_result is None or self._last_scan_result is None:
            return

        entry, bucket_reads, idx_time = self._last_idx_result
        page_id, pages_read, scan_time = self._last_scan_result

        idx_cost = bucket_reads + 1   # buckets lidos + 1 página de dados

        # Calcula o speedup do índice em relação ao scan
        if idx_time > 0 and scan_time > 0:
            speedup = scan_time / idx_time
            speedup_str = f"Indice foi {speedup:.1f}x mais rapido que o Table Scan."
        else:
            speedup_str = "(tempo muito pequeno para calcular speedup)"

        key = self.search_input.text().strip().lower()
        header = f"Palavra buscada: \"{key}\"\n"
        separator = "=" * 58 + "\n"
        col_header = f"{'Metodo':<22} {'Custo (I/Os)':<20} {'Tempo':<14}\n"
        divider = "-" * 58 + "\n"
        idx_row = (
            f"{'Busca por Indice':<22} "
            f"{idx_cost:<20} "
            f"{idx_time * 1000:.4f} ms\n"
        )
        scan_row = (
            f"{'Table Scan':<22} "
            f"{pages_read:<20} "
            f"{scan_time * 1000:.4f} ms\n"
        )

        text = (
            header
            + separator
            + col_header
            + divider
            + idx_row
            + scan_row
            + separator
            + speedup_str
        )
        self.comparison_text.setPlainText(text)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clear_results(self) -> None:
        """Limpa todos os resultados exibidos."""
        self.idx_status_label.setText("—")
        self.idx_status_label.setStyleSheet("")
        self.idx_bucket_hl.deactivate()
        self.idx_chain_label.setText("—")
        self.idx_page_hl.deactivate()
        self.idx_cost_label.setText("—")
        self.idx_time_label.setText("—")

        self.scan_status_label.setText("—")
        self.scan_status_label.setStyleSheet("")
        self.scan_page_hl.deactivate()
        self.scan_cost_label.setText("—")
        self.scan_time_label.setText("—")

        self.comparison_text.setPlainText("")
        self._last_idx_result = None
        self._last_scan_result = None
