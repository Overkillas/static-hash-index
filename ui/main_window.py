"""
Módulo: ui/main_window.py
==========================
Janela principal da aplicação — QMainWindow com sistema de abas (QTabWidget).

Arquitetura do estado compartilhado:
--------------------------------------
A janela principal é o "hub" de dados: ela recebe os resultados de cada painel
e os distribui para os painéis seguintes via sinais Qt. Isso evita acoplamento
direto entre painéis (nenhum painel conhece os outros).

Fluxo de dados:
  LoadPanel ──data_loaded──► MainWindow ──set_pages──► IndexPanel
  IndexPanel ──index_built──► MainWindow ──set_data──► SearchPanel
                                        ──set_index──► StatsPanel

Habilitação progressiva de abas:
  Aba 1 (Carga)       → sempre ativa
  Aba 2 (Índice)      → habilitada após carga do arquivo
  Aba 3 (Busca/Scan)  → habilitada após construção do índice
  Aba 4 (Estatísticas)→ habilitada após construção do índice

Isso guia o usuário pelo fluxo correto de uso.
"""

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
    """
    Janela principal — organiza as 4 abas e gerencia o estado global.

    O estado compartilhado entre painéis é:
      _words:  list[str]   — todas as palavras carregadas
      _pages:  list[Page]  — páginas construídas a partir das palavras
      _index:  HashIndex   — índice hash construído (ou None)
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Indice Hash Estatico — Universidade de Fortaleza")
        self.setMinimumSize(960, 720)

        # Estado global da aplicação
        self._words: list[str] = []
        self._pages: list[Page] = []
        self._index: HashIndex | None = None

        self._setup_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Monta o layout central e o sistema de abas."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(8, 8, 8, 4)
        root_layout.setSpacing(6)

        # ── Cabeçalho informativo ─────────────────────────────────────
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

        # ── Sistema de abas ───────────────────────────────────────────
        self.tabs = QTabWidget()

        # Instancia cada painel
        self.load_panel  = LoadPanel()
        self.index_panel = IndexPanel()
        self.search_panel = SearchPanel()
        self.stats_panel  = StatsPanel()

        self.tabs.addTab(self.load_panel,   "1. Carga de Dados")
        self.tabs.addTab(self.index_panel,  "2. Indice Hash")
        self.tabs.addTab(self.search_panel, "3. Busca & Scan")
        self.tabs.addTab(self.stats_panel,  "4. Estatisticas")

        # Desabilita as abas que dependem de dados ainda não disponíveis
        # O usuário é guiado sequencialmente: Carga → Índice → Busca/Stats
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setTabEnabled(3, False)

        root_layout.addWidget(self.tabs, stretch=1)

        # ── Barra de status ───────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            "Passo 1: carregue um arquivo de palavras na aba 'Carga de Dados'."
        )

    # ------------------------------------------------------------------
    # Conexão de sinais
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """
        Conecta sinais dos painéis ao MainWindow.

        Padrão Observer: os painéis emitem eventos, a janela principal
        decide o que fazer com eles (habilitar abas, passar dados, etc.).
        """
        # Quando o arquivo for carregado → habilita aba de índice
        self.load_panel.data_loaded.connect(self._on_data_loaded)

        # Quando o índice for construído → habilita busca e estatísticas
        self.index_panel.index_built.connect(self._on_index_built)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_data_loaded(self, words: list, pages: list) -> None:
        """
        Chamado quando o LoadPanel termina de carregar e paginar o arquivo.

        Salva o estado, passa dados para o IndexPanel e habilita a Aba 2.

        Args:
            words: Lista de todas as palavras lidas do arquivo.
            pages: Lista de Page com as palavras distribuídas.
        """
        self._words = words
        self._pages = pages

        # Passa as páginas para o painel de índice (atualiza NR e habilita o botão)
        self.index_panel.set_pages(pages)

        # Habilita a aba de índice e navega até ela automaticamente
        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1)

        self.status_bar.showMessage(
            f"Carregado: {len(words):,} palavras | {len(pages):,} paginas — "
            "Passo 2: configure FR e construa o indice na aba 'Indice Hash'."
        )

    def _on_index_built(self, index: HashIndex, elapsed: float) -> None:
        """
        Chamado quando o IndexPanel termina de construir o índice hash.

        Salva o índice, distribui dados para SearchPanel e StatsPanel,
        e habilita as Abas 3 e 4.

        Args:
            index:   O HashIndex recém-construído.
            elapsed: Tempo de construção em segundos.
        """
        self._index = index

        nr = len(self._words)

        # Distribui dados para os painéis dependentes
        self.search_panel.set_data(self._pages, index)
        self.stats_panel.set_index(index, nr, elapsed)

        # Habilita e navega para as abas de busca e estatísticas
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
