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


class LoadWorker(QThread):

    finished = pyqtSignal(list, list)
    error = pyqtSignal(str)

    def __init__(self, filepath: str, page_size: int) -> None:
        super().__init__()
        self.filepath = filepath
        self.page_size = page_size

    def run(self) -> None:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                words = [line.strip().lower() for line in f if line.strip()]

            pages = build_pages(words, self.page_size)
            self.finished.emit(words, pages)

        except Exception as exc:
            self.error.emit(str(exc))


class LoadPanel(QWidget):

    data_loaded = pyqtSignal(list, list)

    def __init__(self) -> None:
        super().__init__()
        self._filepath: str = ""
        self._worker: LoadWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        file_group = QGroupBox("Arquivo de Dados")
        file_layout = QHBoxLayout(file_group)

        self.file_label = QLabel("Nenhum arquivo selecionado.")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label, stretch=1)

        browse_btn = QPushButton("Selecionar Arquivo...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)

        layout.addWidget(file_group)

        config_group = QGroupBox("Configuração de Paginação")
        config_layout = QHBoxLayout(config_group)

        config_layout.addWidget(QLabel("Tamanho da Página (PAGE_SIZE):"))

        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(1, 1_000_000)
        self.page_size_spin.setValue(100)
        self.page_size_spin.setSuffix(" registros/página")
        config_layout.addWidget(self.page_size_spin)
        config_layout.addStretch()

        layout.addWidget(config_group)

        self.load_btn = QPushButton("Carregar e Paginar")
        self.load_btn.setEnabled(False)
        self.load_btn.clicked.connect(self._start_load)
        layout.addWidget(self.load_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

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

    def _browse_file(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo de palavras",
            "",
            "Arquivos de texto (*.txt);;Todos os arquivos (*)",
        )
        if filepath:
            self._filepath = filepath
            self.file_label.setText(filepath)
            self.load_btn.setEnabled(True)

    def _start_load(self) -> None:
        self.load_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Lendo arquivo e criando páginas...")

        page_size = self.page_size_spin.value()
        self._worker = LoadWorker(self._filepath, page_size)
        self._worker.finished.connect(self._on_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_loaded(self, words: list, pages: list) -> None:
        self.progress_bar.hide()
        self.load_btn.setEnabled(True)

        nr = len(words)
        np_ = len(pages)
        page_size = self.page_size_spin.value()

        self.status_label.setText(
            f"Carregado com sucesso:  {nr:,} palavras  |  {np_:,} páginas  "
            f"(PAGE_SIZE = {page_size})"
        )

        first = pages[0]
        self.first_page_text.setPlainText(
            f"Página #{first.page_id}  —  {len(first.records)} registros\n"
            + "-" * 40 + "\n"
            + "\n".join(first.records)
        )

        last = pages[-1]
        self.last_page_text.setPlainText(
            f"Página #{last.page_id}  —  {len(last.records)} registros\n"
            + "-" * 40 + "\n"
            + "\n".join(last.records)
        )

        self.data_loaded.emit(words, pages)

    def _on_error(self, message: str) -> None:
        self.progress_bar.hide()
        self.load_btn.setEnabled(True)
        self.status_label.setText(f"Erro ao carregar arquivo: {message}")
        self.status_label.setStyleSheet("color: red;")
