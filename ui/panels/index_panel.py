from __future__ import annotations

import math

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.hash_index import HashIndex, build_index, calculate_nb
from core.page import Page


class IndexWorker(QThread):

    finished = pyqtSignal(object, float)

    def __init__(self, pages: list[Page], nb: int, fr: int) -> None:
        super().__init__()
        self.pages = pages
        self.nb = nb
        self.fr = fr

    def run(self) -> None:
        index, elapsed = build_index(self.pages, self.nb, self.fr)
        self.finished.emit(index, elapsed)


class IndexPanel(QWidget):

    index_built = pyqtSignal(object, float)

    def __init__(self) -> None:
        super().__init__()
        self._pages: list[Page] = []
        self._nr: int = 0
        self._worker: IndexWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info_label = QLabel(
            "<b>Como funciona:</b> o índice hash mapeia cada palavra a um bucket "
            "usando djb2(key) % NB. Colisões são resolvidas por overflow chaining."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        params_group = QGroupBox("Parâmetros do Índice")
        params_form = QFormLayout(params_group)

        self.fr_spin = QSpinBox()
        self.fr_spin.setRange(1, 1_000_000)
        self.fr_spin.setValue(10)
        self.fr_spin.setSuffix(" entradas/bucket")
        self.fr_spin.valueChanged.connect(self._update_nb_display)
        params_form.addRow("FR — Fator de Recarga:", self.fr_spin)

        self.nb_label = QLabel("—")
        params_form.addRow("NB — Número de Buckets:", self.nb_label)

        self.nr_label = QLabel("Carregue um arquivo primeiro.")
        params_form.addRow("NR — Total de Registros:", self.nr_label)

        formula_label = QLabel(
            "<i>Fórmula: NB = ⌈NR / FR⌉ + 1 "
            "(o +1 garante que NB &gt; NR/FR)</i>"
        )
        params_form.addRow("", formula_label)

        layout.addWidget(params_group)

        self.build_btn = QPushButton("Construir Índice Hash")
        self.build_btn.setEnabled(False)
        self.build_btn.clicked.connect(self._start_build)
        layout.addWidget(self.build_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        results_group = QGroupBox("Resultado da Construção")
        results_form = QFormLayout(results_group)

        self.time_label = QLabel("—")
        results_form.addRow("Tempo de Construção:", self.time_label)

        self.collision_label = QLabel("—")
        results_form.addRow("Total de Colisões:", self.collision_label)

        self.overflow_label = QLabel("—")
        results_form.addRow("Buckets de Overflow Criados:", self.overflow_label)

        layout.addWidget(results_group)
        layout.addStretch()

    def set_pages(self, pages: list[Page]) -> None:
        self._pages = pages
        self._nr = sum(len(p.records) for p in pages)
        self.nr_label.setText(f"{self._nr:,} registros")
        self._update_nb_display()
        self.build_btn.setEnabled(True)

    def _update_nb_display(self) -> None:
        if self._nr == 0:
            self.nb_label.setText("—")
            return
        fr = self.fr_spin.value()
        nb = calculate_nb(self._nr, fr)
        raw = math.ceil(self._nr / fr)
        self.nb_label.setText(
            f"{nb} buckets  [= ceil({self._nr} / {fr}) + 1 = {raw} + 1]"
        )

    def _start_build(self) -> None:
        fr = self.fr_spin.value()
        nb = calculate_nb(self._nr, fr)

        self.build_btn.setEnabled(False)
        self.progress_bar.show()
        self.time_label.setText("Construindo índice...")
        self.collision_label.setText("—")
        self.overflow_label.setText("—")

        self._worker = IndexWorker(self._pages, nb, fr)
        self._worker.finished.connect(self._on_built)
        self._worker.start()

    def _on_built(self, index: HashIndex, elapsed: float) -> None:
        self.progress_bar.hide()
        self.build_btn.setEnabled(True)

        self.time_label.setText(f"{elapsed:.4f} segundos")
        self.collision_label.setText(f"{index.collision_count:,} inserções")
        self.overflow_label.setText(f"{index.overflow_count:,} buckets")

        self.index_built.emit(index, elapsed)
