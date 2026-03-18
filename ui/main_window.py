from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.hash_index import HashIndex
from core.page import Page
from ui.panels.index_panel import IndexPanel
from ui.panels.load_panel import LoadPanel
from ui.panels.search_panel import SearchPanel
from ui.panels.stats_panel import StatsPanel


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Indice Hash Estatico — Universidade de Fortaleza")
        self.setMinimumSize(960, 720)

        self._words: list[str] = []
        self._pages: list[Page] = []
        self._index: HashIndex | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(8, 8, 8, 4)
        root_layout.setSpacing(6)

        header = QLabel(
            "<b>Indice Hash</b>"
        )
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(
            "font-size: 13px; "
            "padding: 6px; "
            "background-color: #E3F2FD; "
            "border-radius: 4px;"
        )
        root_layout.addWidget(header)

        self.tabs = QTabWidget()

        self.load_panel  = LoadPanel()
        self.index_panel = IndexPanel()
        self.search_panel = SearchPanel()
        self.stats_panel  = StatsPanel()

        self.tabs.addTab(self.load_panel,   "1. Carga de Dados")
        self.tabs.addTab(self.index_panel,  "2. Indice Hash")
        self.tabs.addTab(self.search_panel, "3. Busca & Scan")
        self.tabs.addTab(self.stats_panel,  "4. Estatisticas")

        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setTabEnabled(3, False)

        root_layout.addWidget(self.tabs, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            "Passo 1: carregue um arquivo de palavras na aba 'Carga de Dados'."
        )

    def _connect_signals(self) -> None:
        self.load_panel.data_loaded.connect(self._on_data_loaded)
        self.index_panel.index_built.connect(self._on_index_built)

    def _on_data_loaded(self, words: list, pages: list) -> None:
        self._words = words
        self._pages = pages

        self.index_panel.set_pages(pages)

        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1)

        self.status_bar.showMessage(
            f"Carregado: {len(words):,} palavras | {len(pages):,} paginas — "
            "Passo 2: configure FR e construa o indice na aba 'Indice Hash'."
        )

    def _on_index_built(self, index: HashIndex, elapsed: float) -> None:
        self._index = index

        nr = len(self._words)

        self.search_panel.set_data(self._pages, index)
        self.stats_panel.set_index(index, nr, elapsed)

        self.tabs.setTabEnabled(2, True)
        self.tabs.setTabEnabled(3, True)
        self.tabs.setCurrentIndex(2)

        self.status_bar.showMessage(
            f"Indice construido: {index.nb:,} buckets (FR={index.fr}) em "
            f"{elapsed:.3f}s | "
            f"Colisoes: {index.collision_count:,} | "
            f"Overflows: {index.overflow_count:,} — "
            "Passo 3: use a aba 'Busca & Scan' para pesquisar palavras."
        )
