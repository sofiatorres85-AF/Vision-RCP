@echo off
REM Ejecuta el sistema de RCP con el venv (define Tcl/Tk para Windows 3.13)
set TCL_LIBRARY=%~dp0venv\tcl\tcl8.6
set TK_LIBRARY=%~dp0venv\tcl\tk8.6
.\venv\Scripts\python main.py
pause