"""
Módulo: ui/panels/stats_panel.py
==================================
Painel de estatísticas — Aba 4 da interface.

Responsabilidades (HU12, HU13):
  - HU12: Exibir a taxa de colisão (%) com barra visual.
  - HU13: Exibir a taxa de overflow (%) com barra visual.

Métricas exibidas:
  ┌─────────────────────────────────────────────────────────────────┐
  │  Taxa de Colisão  (%)  =  (colisões / NR) × 100                │
  │  Taxa de Overflow (%)  =  (overflows / NB) × 100               │
  │  NR = total de registros inseridos no índice                    │
  │  NB = número de buckets primários                               │
  │  FR = fator de recarga (entradas por bucket)                    │
  │  Tempo de construção do índice                                  │
  └─────────────────────────────────────────────────────────────────┘

Quando é atualizado:
  - Após a construção do índice (IndexPanel emite `index_built`).
  - A janela principal chama `set_index()` com os dados do índice.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from core.hash_index import HashIndex


# ---------------------------------------------------------------------------
# Widget auxiliar: Card de métrica com barra de progresso
# ---------------------------------------------------------------------------

class MetricCard(QWidget):
    """
    Card visual que exibe um título, um valor percentual e uma barra de progresso.

    Args:
        title:       Título da métrica (exibido em negrito no topo).
        bar_color:   Cor da barra de progresso (formato CSS, ex: "#FF5722").
        tooltip:     Texto de tooltip explicativo.
    """

    def __init__(
        self,
        title: str,
        bar_color: str = "#2196F3",
        tooltip: str = "",
    ) -> None:
        super().__init__()
        if tooltip:
            self.setToolTip(tooltip)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Título
        title_lbl = QLabel(f"<b>{title}</b>")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        # Valor numérico (grande)
        self.value_label = QLabel("—")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(self.value_label)

        # Sub-label com contagem absoluta
        self.sub_label = QLabel("")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(self.sub_label)

        # Barra de progresso visual
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)   # escala x10 para suportar frações
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(18)
        self.bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid #bbb;
                border-radius: 4px;
                background-color: #f5f5f5;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 3px;
            }}
            """
        )
        layout.addWidget(self.bar)

        # Estilo do card
        self.setStyleSheet(
            """
            MetricCard {
                border: 1px solid #ddd;
                border-radius: 10px;
                background-color: #fafafa;
            }
            """
        )
        self.setMinimumWidth(200)

    def set_value(self, percent: float, sub_text: str = "") -> None:
        """
        Atualiza o valor exibido no card.

        Args:
            percent:  Valor percentual (0.0 a 100.0).
            sub_text: Texto opcional abaixo do valor (ex: "1234 colisões").
        """
        self.value_label.setText(f"{percent:.2f}%")
        self.sub_label.setText(sub_text)
        # Escala para 0-1000 para preservar 1 casa decimal na barra
        bar_val = int(min(percent * 10, 1000))
        self.bar.setValue(bar_val)


# ---------------------------------------------------------------------------
# Painel principal
# ---------------------------------------------------------------------------

class StatsPanel(QWidget):
    """
    Painel de estatísticas do índice hash — Aba 4.

    Exibe as métricas calculadas após a construção do índice.
    """

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # ── Cards de taxa (parte superior) ───────────────────────────
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        self.collision_card = MetricCard(
            title="Taxa de Colisao (%)",
            bar_color="#EF5350",
            tooltip=(
                "Taxa de Colisao = (total_colisoes / NR) × 100\n"
                "Colisao: inserção que encontrou o bucket primário cheio."
            ),
        )

        self.overflow_card = MetricCard(
            title="Taxa de Overflow (%)",
            bar_color="#AB47BC",
            tooltip=(
                "Taxa de Overflow = (buckets_overflow / NB) × 100\n"
                "Overflow: novo bucket encadeado criado quando o primário está cheio."
            ),
        )

        cards_layout.addWidget(self.collision_card)
        cards_layout.addWidget(self.overflow_card)
        layout.addLayout(cards_layout)

        # ── Detalhes do índice ────────────────────────────────────────
        details_group = QGroupBox("Detalhes do Indice Construido")
        details_form = QFormLayout(details_group)
        details_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        details_form.setSpacing(6)

        self.nr_label = QLabel("—")
        details_form.addRow("Total de Registros (NR):", self.nr_label)

        self.nb_label = QLabel("—")
        details_form.addRow("Buckets Primarios (NB):", self.nb_label)

        self.fr_label = QLabel("—")
        details_form.addRow("Fator de Recarga (FR):", self.fr_label)

        self.collision_abs_label = QLabel("—")
        details_form.addRow("Colisoes (absoluto):", self.collision_abs_label)

        self.overflow_abs_label = QLabel("—")
        details_form.addRow("Buckets de Overflow Criados:", self.overflow_abs_label)

        self.build_time_label = QLabel("—")
        details_form.addRow("Tempo de Construcao:", self.build_time_label)

        layout.addWidget(details_group)

        # ── Fórmulas de referência ────────────────────────────────────
        formulas_group = QGroupBox("Formulas de Calculo")
        formulas_layout = QVBoxLayout(formulas_group)

        formulas_label = QLabel(
            "<pre>"
            "  NB              = ceil(NR / FR) + 1\n"
            "  Taxa Colisao    = (colisoes / NR) × 100\n"
            "  Taxa Overflow   = (overflows / NB) × 100\n"
            "  Custo Indice    = leituras_bucket + 1  (minimo = 2 I/Os)\n"
            "  Custo Scan      = paginas lidas ate encontrar\n"
            "</pre>"
        )
        formulas_label.setWordWrap(False)
        formulas_layout.addWidget(formulas_label)

        layout.addWidget(formulas_group)
        layout.addStretch()

    # ------------------------------------------------------------------
    # Interface pública (chamada pela MainWindow)
    # ------------------------------------------------------------------

    def set_index(self, index: HashIndex, nr: int, build_time: float) -> None:
        """
        Atualiza todas as métricas com os dados do índice recém-construído.

        Args:
            index:      O HashIndex construído pelo IndexPanel.
            nr:         Número total de registros inseridos no índice.
            build_time: Tempo de construção em segundos (float).
        """
        nb = index.nb
        fr = index.fr
        collision_count = index.collision_count
        overflow_count = index.overflow_count

        # ── Cálculo das taxas ─────────────────────────────────────────
        # Taxa de colisão: proporção de inserções que encontraram o bucket
        # primário cheio em relação ao total de registros.
        collision_rate = (collision_count / nr * 100) if nr > 0 else 0.0

        # Taxa de overflow: proporção de buckets de overflow criados em
        # relação ao número de buckets primários.
        overflow_rate = (overflow_count / nb * 100) if nb > 0 else 0.0

        # ── Atualiza os cards ─────────────────────────────────────────
        self.collision_card.set_value(
            collision_rate,
            sub_text=f"{collision_count:,} colisoes de {nr:,} inserções",
        )
        self.overflow_card.set_value(
            overflow_rate,
            sub_text=f"{overflow_count:,} buckets de {nb:,} primarios",
        )

        # ── Atualiza os labels de detalhes ────────────────────────────
        self.nr_label.setText(f"{nr:,} registros")
        self.nb_label.setText(f"{nb:,} buckets")
        self.fr_label.setText(f"{fr} entradas/bucket")
        self.collision_abs_label.setText(
            f"{collision_count:,}  ({collision_rate:.4f}% dos registros)"
        )
        self.overflow_abs_label.setText(
            f"{overflow_count:,}  ({overflow_rate:.4f}% dos buckets primarios)"
        )
        self.build_time_label.setText(f"{build_time:.4f} segundos")
