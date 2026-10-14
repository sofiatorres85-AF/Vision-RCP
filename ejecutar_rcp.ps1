# Ejecutar app RCP con el venv (fix Tcl/Tk en Windows)
$env:TCL_LIBRARY = 'C:\Users\lucas\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
$env:TK_LIBRARY = 'C:\Users\lucas\AppData\Local\Programs\Python\Python313\tcl\tk8.6'
.\venv\Scripts\python app_rcp_aruco_pose.py
