"""
Arquivo: main.py
=================
Entrypoint da aplicação Índice Hash Estático.

Como executar:
    uv run main.py

O que este arquivo faz:
    1. Inicializa a aplicação PyQt6 (QApplication).
    2. Cria a janela principal (MainWindow).
    3. Exibe a janela.
    4. Inicia o loop de eventos Qt (app.exec).
    5. Ao fechar a janela, encerra o processo com o código de saída correto.

Por que sys.exit(app.exec())?
    app.exec() bloqueia até que a janela seja fechada e retorna um código
    de saída (0 = sucesso). sys.exit() repassa esse código ao sistema
    operacional — importante para scripts e integração com terminais.
"""

import sys

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> None:
    """
    Ponto de entrada principal da aplicação.

    Cria o QApplication (necessário antes de qualquer widget PyQt6),
    instancia a janela principal e inicia o loop de eventos.
    """
    # QApplication gerencia o loop de eventos e recursos gráficos.
    # sys.argv permite ao Qt receber argumentos de linha de comando
    # (como --style, --platform, etc.).
    app = QApplication(sys.argv)

    app.setApplicationName("Indice Hash Estatico")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("UNIFOR — Universidade de Fortaleza")

    # Cria e exibe a janela principal
    window = MainWindow()
    window.show()

    # Inicia o loop de eventos — bloqueia até a janela ser fechada
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
