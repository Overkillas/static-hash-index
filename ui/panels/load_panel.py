"""
Módulo: ui/panels/load_panel.py
================================
Painel de carga de dados — Aba 1 da interface.

Responsabilidades (HU01, HU02, HU03):
  - HU01: Permitir ao usuário selecionar o arquivo words_alpha.txt.
  - HU02: Configurar o PAGE_SIZE via spinbox.
  - HU03: Carregar o arquivo, distribuir palavras em páginas e mostrar
          preview da primeira e da última página.

Fluxo de uso:
  1. Usuário clica "Selecionar Arquivo" → escolhe o .txt.
  2. Ajusta PAGE_SIZE (padrão 100).
  3. Clica "Carregar e Paginar".
  4. Um LoadWorker (QThread) lê o arquivo em background → UI não trava.
  5. Ao terminar, exibe totais e preview das páginas.
  6. Emite o sinal `data_loaded` para que a janela principal habilite
     a aba de índice.

Por que usar QThread para carregar o arquivo?
-----------------------------------------------
Ler 466k palavras do disco e criar ~4.660 objetos Page pode demorar
1-3 segundos. Se feito na thread principal (UI), a janela "travaria"
durante esse tempo. QThread executa a operação em paralelo, mantendo
a UI responsiva com uma barra de progresso animada.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.page import Page, build_pages


# ---------------------------------------------------------------------------
# Worker — executa em background para não travar a UI
# ---------------------------------------------------------------------------

class LoadWorker(QThread):
    """
    Worker que lê o arquivo .txt e constrói as páginas em uma thread separada.

    Emite:
        finished(words: list[str], pages: list[Page]): quando concluído.
        error(message: str): quando ocorre qualquer exceção.
    """

    finished = pyqtSignal(list, list)   # (words, pages)
    error = pyqtSignal(str)

    def __init__(self, filepath: str, page_size: int) -> None:
        super().__init__()
        self.filepath = filepath
        self.page_size = page_size

    def run(self) -> None:
        """
        Corpo da thread: lê o arquivo linha a linha e pagina as palavras.

        Cada linha do arquivo contém uma palavra. Linhas vazias são ignoradas.
        As palavras são armazenadas em minúsculas e sem espaços extras.
        """
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                # Lê todas as linhas, remove espaços e descarta linhas vazias
                words = [line.strip().lower() for line in f if line.strip()]

            # Divide as palavras em páginas de tamanho page_size
            pages = build_pages(words, self.page_size)

            # Emite sinal com o resultado para a thread principal (UI)
            self.finished.emit(words, pages)

        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Painel principal
# ---------------------------------------------------------------------------

class LoadPanel(QWidget):
    """
    Painel de carga de dados — Aba 1.

    Signals:
        data_loaded(words: list[str], pages: list[Page]):
            Emitido quando o arquivo foi lido e as páginas construídas.
            A janela principal escuta este sinal para habilitar a Aba 2.
    """

    data_loaded = pyqtSignal(list, list)

    def __init__(self) -> None:
        super().__init__()
        self._filepath: str = ""
        self._worker: LoadWorker | None = None
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Grupo: Seleção de arquivo ─────────────────────────────────
        file_group = QGroupBox("Arquivo de Dados")
        file_layout = QHBoxLayout(file_group)

        self.file_label = QLabel("Nenhum arquivo selecionado.")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label, stretch=1)

        browse_btn = QPushButton("Selecionar Arquivo...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)

        layout.addWidget(file_group)

        # ── Grupo: Configuração de PAGE_SIZE ──────────────────────────
        config_group = QGroupBox("Configuração de Paginação")
        config_layout = QHBoxLayout(config_group)

        config_layout.addWidget(QLabel("Tamanho da Página (PAGE_SIZE):"))

        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(1, 1_000_000)
        self.page_size_spin.setValue(100)   # padrão recomendado
        self.page_size_spin.setSuffix(" registros/página")
        config_layout.addWidget(self.page_size_spin)
        config_layout.addStretch()

        layout.addWidget(config_group)

        # ── Botão de carga ────────────────────────────────────────────
        self.load_btn = QPushButton("Carregar e Paginar")
        self.load_btn.setEnabled(False)
        self.load_btn.clicked.connect(self._start_load)
        layout.addWidget(self.load_btn)

        # ── Barra de progresso (indeterminada — aparece durante a carga) ─
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 0,0 = animação de progresso indeterminado
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # ── Rótulo de status ──────────────────────────────────────────
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # ── Preview: primeira e última página ─────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        first_group = QGroupBox("Primeira Página (page_id = 0)")
        first_layout = QVBoxLayout(first_group)
        self.first_page_text = QTextEdit()
        self.first_page_text.setReadOnly(True)
        self.first_page_text.setPlaceholderText("Aguardando carga do arquivo...")
        first_layout.addWidget(self.first_page_text)

        last_group = QGroupBox("Última Página (page_id = N-1)")
        last_layout = QVBoxLayout(last_group)
        self.last_page_text = QTextEdit()
        self.last_page_text.setReadOnly(True)
        self.last_page_text.setPlaceholderText("Aguardando carga do arquivo...")
        last_layout.addWidget(self.last_page_text)

        splitter.addWidget(first_group)
        splitter.addWidget(last_group)
        layout.addWidget(splitter, stretch=1)

    # ------------------------------------------------------------------
    # Handlers de eventos
    # ------------------------------------------------------------------

    def _browse_file(self) -> None:
        """Abre diálogo de seleção de arquivo .txt."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo de palavras",
            "",
            "Arquivos de texto (*.txt);;Todos os arquivos (*)",
        )
        if filepath:
            self._filepath = filepath
            # Exibe apenas o nome do arquivo (não o caminho completo)
            self.file_label.setText(filepath)
            self.load_btn.setEnabled(True)

    def _start_load(self) -> None:
        """Inicia o worker de carga em background."""
        self.load_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Lendo arquivo e criando páginas...")

        page_size = self.page_size_spin.value()
        self._worker = LoadWorker(self._filepath, page_size)
        self._worker.finished.connect(self._on_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_loaded(self, words: list, pages: list) -> None:
        """Callback invocado na thread principal quando a carga termina."""
        self.progress_bar.hide()
        self.load_btn.setEnabled(True)

        nr = len(words)
        np_ = len(pages)
        page_size = self.page_size_spin.value()

        self.status_label.setText(
            f"Carregado com sucesso:  {nr:,} palavras  |  {np_:,} páginas  "
            f"(PAGE_SIZE = {page_size})"
        )

        # ── Preview da primeira página ────────────────────────────────
        first = pages[0]
        self.first_page_text.setPlainText(
            f"Página #{first.page_id}  —  {len(first.records)} registros\n"
            + "-" * 40 + "\n"
            + "\n".join(first.records)
        )

        # ── Preview da última página ──────────────────────────────────
        last = pages[-1]
        self.last_page_text.setPlainText(
            f"Página #{last.page_id}  —  {len(last.records)} registros\n"
            + "-" * 40 + "\n"
            + "\n".join(last.records)
        )

        # Notifica a janela principal para habilitar a aba de índice
        self.data_loaded.emit(words, pages)

    def _on_error(self, message: str) -> None:
        """Callback invocado quando ocorre erro durante a carga."""
        self.progress_bar.hide()
        self.load_btn.setEnabled(True)
        self.status_label.setText(f"Erro ao carregar arquivo: {message}")
        self.status_label.setStyleSheet("color: red;")
