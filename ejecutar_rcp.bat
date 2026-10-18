@echo off
REM Ejecuta el sistema de RCP con el venv (define Tcl/Tk para Windows 3.13)
set TCL_LIBRARY=C:\Users\lucas\AppData\Local\Programs\Python\Python313\tcl\tcl8.6
set TK_LIBRARY=C:\Users\lucas\AppData\Local\Programs\Python\Python313\tcl\tk8.6
.\venv\Scripts\python main.py
pause