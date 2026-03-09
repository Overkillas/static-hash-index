"""
Módulo: ui/panels/index_panel.py
==================================
Painel de construção do índice hash — Aba 2 da interface.

Responsabilidades (HU04, HU05, HU06, HU07, HU08):
  - HU04: Criar NB buckets de capacidade FR.
  - HU05: Exibir a função hash configurável (FR ajustável, NB calculado).
  - HU06: Construir o índice percorrendo todas as páginas.
  - HU07: Resolver colisões com overflow chaining (implementado no core).
  - HU08: Exibir resultado da construção: tempo, colisões, overflows.

Fluxo de uso:
  1. A aba só fica ativa após o painel de carga emitir `data_loaded`.
  2. O usuário ajusta FR (Fator de Recarga) — NB é recalculado automaticamente.
  3. Clica "Construir Índice Hash".
  4. Um IndexWorker (QThread) constrói o índice em background.
  5. Ao terminar, exibe: tempo de construção, colisões, overflows.
  6. Emite `index_built` para habilitar as abas de Busca e Estatísticas.

Por que QThread para construir o índice?
------------------------------------------
Com 466k registros, a construção do índice pode levar 5-15 segundos em Python
puro. Usar QThread mantém a interface responsiva durante todo esse processo.
"""

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


# ---------------------------------------------------------------------------
# Worker — constrói o índice em background
# ---------------------------------------------------------------------------

class IndexWorker(QThread):
    """
    Worker que constrói o índice hash em uma thread separada.

    Emite:
        finished(index: HashIndex, elapsed: float):
            Emitido com o índice pronto e o tempo de construção em segundos.
    """

    finished = pyqtSignal(object, float)   # (HashIndex, elapsed_seconds)

    def __init__(self, pages: list[Page], nb: int, fr: int) -> None:
        super().__init__()
        self.pages = pages
        self.nb = nb
        self.fr = fr

    def run(self) -> None:
        """Chama build_index do core e emite o resultado."""
        index, elapsed = build_index(self.pages, self.nb, self.fr)
        self.finished.emit(index, elapsed)


# ---------------------------------------------------------------------------
# Painel principal
# ---------------------------------------------------------------------------

class IndexPanel(QWidget):
    """
    Painel de construção do índice hash — Aba 2.

    Signals:
        index_built(index: HashIndex, elapsed: float):
            Emitido quando o índice foi construído com sucesso.
            A janela principal escuta este sinal para habilitar as Abas 3 e 4.
    """

    index_built = pyqtSignal(object, float)

    def __init__(self) -> None:
        super().__init__()
        self._pages: list[Page] = []
        self._nr: int = 0                    # total de registros
        self._worker: IndexWorker | None = None
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Explicação do módulo ──────────────────────────────────────
        info_label = QLabel(
            "<b>Como funciona:</b> o índice hash mapeia cada palavra a um bucket "
            "usando djb2(key) % NB. Colisões são resolvidas por overflow chaining."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # ── Grupo: Parâmetros ─────────────────────────────────────────
        params_group = QGroupBox("Parâmetros do Índice")
        params_form = QFormLayout(params_group)

        # FR — Fator de Recarga
        self.fr_spin = QSpinBox()
        self.fr_spin.setRange(1, 10_000)
        self.fr_spin.setValue(10)   # padrão: 10 entradas/bucket
        self.fr_spin.setSuffix(" entradas/bucket")
        self.fr_spin.valueChanged.connect(self._update_nb_display)
        params_form.addRow("FR — Fator de Recarga:", self.fr_spin)

        # NB — exibido automaticamente (somente leitura)
        self.nb_label = QLabel("—")
        params_form.addRow("NB — Número de Buckets:", self.nb_label)

        # NR — informativo
        self.nr_label = QLabel("Carregue um arquivo primeiro.")
        params_form.addRow("NR — Total de Registros:", self.nr_label)

        # Fórmula NB
        formula_label = QLabel(
            "<i>Fórmula: NB = ⌈NR / FR⌉ + 1 "
            "(o +1 garante que NB &gt; NR/FR)</i>"
        )
        params_form.addRow("", formula_label)

        layout.addWidget(params_group)

        # ── Botão de construção ───────────────────────────────────────
        self.build_btn = QPushButton("Construir Índice Hash")
        self.build_btn.setEnabled(False)
        self.build_btn.clicked.connect(self._start_build)
        layout.addWidget(self.build_btn)

        # ── Barra de progresso indeterminada ──────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # ── Grupo: Resultado da construção ────────────────────────────
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

    # ------------------------------------------------------------------
    # Interface pública (chamada pela MainWindow)
    # ------------------------------------------------------------------

    def set_pages(self, pages: list[Page]) -> None:
        """
        Recebe as páginas do LoadPanel e habilita o botão de construção.

        Args:
            pages: Lista de páginas gerada pelo LoadPanel.
        """
        self._pages = pages
        self._nr = sum(len(p.records) for p in pages)
        self.nr_label.setText(f"{self._nr:,} registros")
        self._update_nb_display()
        self.build_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Lógica interna
    # ------------------------------------------------------------------

    def _update_nb_display(self) -> None:
        """Recalcula e exibe NB sempre que FR é alterado."""
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
        """Inicia a construção do índice em background via IndexWorker."""
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
        """Callback chamado na thread da UI quando a construção termina."""
        self.progress_bar.hide()
        self.build_btn.setEnabled(True)

        self.time_label.setText(f"{elapsed:.4f} segundos")
        self.collision_label.setText(f"{index.collision_count:,} inserções")
        self.overflow_label.setText(f"{index.overflow_count:,} buckets")

        # Propaga o índice para a janela principal → habilita abas 3 e 4
        self.index_built.emit(index, elapsed)
