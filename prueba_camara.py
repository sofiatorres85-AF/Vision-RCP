import cv2

camara = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not camara.isOpened():
    print("ERROR: No se pudo abrir la cámara.")
    exit()

print("Cámara iniciada correctamente.")
print("Presiona Q para salir.")

while True:
    ret, frame = camara.read()

    if not ret:
        print("ERROR: No se pudo capturar la imagen.")
        break

    cv2.imshow("Prueba de cámara - Proyecto RCP", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camara.release()
cv2.destroyAllWindows()