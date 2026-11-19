"""Punto de entrada: sin argumentos abre la interfaz gráfica; con argumentos, el CLI."""

import sys


def main() -> int:
    if len(sys.argv) > 1:
        from .cli import main as cli_main
        return cli_main()
    from .ui.app import run
    return run()


if __name__ == "__main__":
    sys.exit(main())
