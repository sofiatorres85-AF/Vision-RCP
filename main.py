"""Punto de entrada del sistema de análisis de técnica RCP.

Uso::

    venv\\Scripts\\python main.py

Tkinter en el venv de Windows puede requerir las variables TCL_LIBRARY y
TK_LIBRARY; ``ejecutar_rcp.bat`` las define antes de invocar este script.
"""

from __future__ import annotations

import sys
import tkinter as tk

from rcp.configuracion import Configuracion
from rcp.interfaz import AplicacionRCP


def main() -> int:
    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(f"ERROR de Tkinter: {error}", file=sys.stderr)
        print("En Windows define TCL_LIBRARY y TK_LIBRARY, o usa ejecutar_rcp.bat.", file=sys.stderr)
        return 1

    AplicacionRCP(root, Configuracion())
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())