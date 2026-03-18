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


class HighlightLabel(QLabel):

    STYLE_BUCKET = ("#E65100", "#FFFFFF", "#BF360C")
    STYLE_INDEX  = ("#1B5E20", "#FFFFFF", "#004D00")
    STYLE_SCAN   = ("#0D47A1", "#FFFFFF", "#002171")
    STYLE_ERROR  = ("#B71C1C", "#FFFFFF", "#7F0000")
    STYLE_OFF    = ("#EEEEEE", "#424242", "#BDBDBD")

    def __init__(self, text: str = "", active_style: tuple = STYLE_BUCKET) -> None:
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._active_style = active_style
        self._apply_style(*self.STYLE_OFF)

    def activate(self, text: str) -> None:
        self.setText(text)
        self._apply_style(*self._active_style)

    def deactivate(self, text: str = "—") -> None:
        self.setText(text)
        self._apply_style(*self.STYLE_OFF)

    def set_error(self, text: str) -> None:
        self.setText(text)
        self._apply_style(*self.STYLE_ERROR)

    def _apply_style(self, bg: str, fg: str, border: str) -> None:
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


class SearchPanel(QWidget):

    def __init__(self) -> None:
        super().__init__()
        self._pages: list[Page] = []
        self._index: HashIndex | None = None
        self._last_idx_result: tuple | None = None
        self._last_scan_result: tuple | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        search_group = QGroupBox("Palavra a Buscar")
        search_layout = QHBoxLayout(search_group)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Digite uma palavra em inglês... (ex: apple)")
        self.search_input.returnPressed.connect(self._do_both)
        search_layout.addWidget(self.search_input, stretch=1)

        self.idx_btn = QPushButton("Buscar por Indice")
        self.idx_btn.setEnabled(False)
        self.idx_btn.clicked.connect(self._do_index_search)
        search_layout.addWidget(self.idx_btn)

        self.scan_btn = QPushButton("Table Scan")
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self._do_scan)
        search_layout.addWidget(self.scan_btn)

        self.both_btn = QPushButton("Buscar Ambos")
        self.both_btn.setEnabled(False)
        self.both_btn.clicked.connect(self._do_both)
        search_layout.addWidget(self.both_btn)

        layout.addWidget(search_group)

        results_layout = QHBoxLayout()

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

    def set_data(self, pages: list[Page], index: HashIndex) -> None:
        self._pages = pages
        self._index = index
        self.idx_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.both_btn.setEnabled(True)
        self._clear_results()

    def _do_index_search(self) -> None:
        if self._index is None:
            return

        key = self.search_input.text().strip().lower()
        if not key:
            return

        entry, bucket_reads, elapsed = search_index(self._index, key)

        primary_id = hash_function(key, self._index.nb)
        primary_bucket = self._index.buckets[primary_id]

        if entry is not None:
            self.idx_status_label.setText(
                f'Encontrada: "{key}"'
            )
            self.idx_status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")

            self.idx_bucket_hl.activate(
                f"Bucket #{primary_id}  ({bucket_reads} leitura(s))"
            )

            chain_str = primary_bucket.get_chain_summary()
            if len(chain_str) > 120:
                chain_str = chain_str[:120] + "..."
            self.idx_chain_label.setText(chain_str)

            self.idx_page_hl.activate(f"Pagina #{entry.page_id}")

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
        if not self._pages:
            return

        key = self.search_input.text().strip().lower()
        if not key:
            return

        page_id, pages_read, elapsed = do_table_scan(self._pages, key)

        if page_id is not None:
            self.scan_status_label.setText(f'Encontrada: "{key}"')
            self.scan_status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
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
        key = self.search_input.text().strip().lower()
        if not key:
            return
        self._do_index_search()
        self._do_scan()

    def _try_update_comparison(self) -> None:
        if self._last_idx_result is None or self._last_scan_result is None:
            return

        entry, bucket_reads, idx_time = self._last_idx_result
        page_id, pages_read, scan_time = self._last_scan_result

        idx_cost = bucket_reads + 1 if entry is not None else bucket_reads

        if idx_time > 0 and scan_time > 0:
            speedup = scan_time / idx_time
            time_diff_pct = ((scan_time - idx_time) / scan_time) * 100
            speedup_str = (
                f"Indice foi {speedup:.1f}x mais rapido que o Table Scan.\n"
                f"Diferenca percentual de tempo: {time_diff_pct:.2f}%\n"
                f"Diferenca de custo (I/Os): {pages_read} (scan) vs {idx_cost} (indice)"
            )
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

    def _clear_results(self) -> None:
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
