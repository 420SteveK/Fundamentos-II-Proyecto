import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2
import pygame
import socket
import threading

# -------------------- CLASE CONEXIÓN RASPBERRY --------------------
class Raspberry:
    def __init__(self, ip="10.102.56.46", port=1717):
        self.server_ip = ip
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False

    def conected(self):
        try:
            self.client_socket.connect((self.server_ip, self.port))
            self.connected = True
            threading.Thread(target=self.receive_messages, daemon=True).start()
            print("Conectado a Raspberry Pico W")
        except Exception as e:
            print(f"Error al conectar: {e}")

    def receive_messages(self):
        while True:
            try:
                msg = self.client_socket.recv(1024).decode()
                print(f"Raspberry: {msg}")
            except:
                break

    def close(self):
        if self.connected:
            self.client_socket.close()

# -------------------- VARIABLES GLOBALES DE EQUIPOS --------------------
equipos_seleccionados = {"equipo1": None, "equipo2": None}
equipo_actual = 1  # Controla si toca seleccionar el primer o segundo equipo

# -------------------- CLASE VENTANA EQUIPO --------------------
class VentanaEquipo:
    def __init__(self, master, titulo, imagenes, nombres, sonido=None, video_path=None, imagenes_porteros=None, nombres_porteros=None):
        self.master = master
        self.titulo = titulo
        self.imagenes = imagenes
        self.nombres = nombres
        self.sonido = sonido
        self.video_path = video_path
        self.imagenes_porteros = imagenes_porteros or []
        self.nombres_porteros = nombres_porteros or []
        self.jugador_seleccionado_nombre = None  # ### NUEVO ###
        self.portero_seleccionado_nombre = None  # ### NUEVO ###

        self.master.withdraw()  # Oculta la ventana principal

        # Crear la ventana del equipo
        self.ventana = tk.Toplevel(master)
        self.ventana.title(self.titulo)
        self.ventana.geometry("850x478")

        # Reproducir sonido si existe
        if self.sonido:
            pygame.mixer.music.load(self.sonido)
            pygame.mixer.music.play(loops=-1)

        # Reproducir video de fondo
        self.cap = None
        if self.video_path:
            self.cap = cv2.VideoCapture(self.video_path)
            self.label_fondo = tk.Label(self.ventana)
            self.label_fondo.place(x=0, y=0, relwidth=1, relheight=1)
            self.actualizar_fondo()

        # Cargar imágenes iniciales (jugadores)
        self.imagenes_tk = []
        self.mostrar_jugadores(self.imagenes, self.nombres)

        # Detener música y liberar video al cerrar
        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)

    def actualizar_fondo(self):
        if self.cap:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (850, 478))
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.label_fondo.imgtk = imgtk
                self.label_fondo.config(image=imgtk)
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.ventana.after(20, self.actualizar_fondo)

    def mostrar_jugadores(self, imagenes, nombres):
        # Eliminar botones existentes (sin eliminar el video de fondo)
        for widget in self.ventana.winfo_children():
            if isinstance(widget, tk.Button):
                widget.destroy()

        self.imagenes_tk = []
        posiciones = [(220, 400), (510, 400), (800, 400)]

        for i, (img_path, nombre) in enumerate(zip(imagenes, nombres)):
            img = ImageTk.PhotoImage(Image.open(img_path).resize((180, 275)))
            self.imagenes_tk.append(img)
            x, y = posiciones[i]
            tk.Button(
                self.ventana,
                image=img,
                borderwidth=0,
                command=lambda n=nombre: self.jugador_seleccionado(n)
            ).place(x=x, y=y, anchor="se")

    def jugador_seleccionado(self, nombre):
        self.jugador_seleccionado_nombre = nombre
        print(f"{nombre} seleccionado como jugador")
        messagebox.showinfo("Jugador seleccionado", f"{nombre}")

        # Mostrar porteros tras seleccionar jugador
        if self.imagenes_porteros and self.nombres_porteros:
            self.mostrar_porteros()

    def mostrar_porteros(self):
        # Mostrar botones de porteros
        self.imagenes_tk = []
        posiciones = [(220, 400), (510, 400), (800, 400)]
        for i, (img_path, nombre) in enumerate(zip(self.imagenes_porteros, self.nombres_porteros)):
            img = ImageTk.PhotoImage(Image.open(img_path).resize((180, 275)))
            self.imagenes_tk.append(img)
            x, y = posiciones[i]
            tk.Button(
                self.ventana,
                image=img,
                borderwidth=0,
                command=lambda n=nombre: self.portero_seleccionado(n)
            ).place(x=x, y=y, anchor="se")

    def portero_seleccionado(self, nombre):
        global equipo_actual
        self.portero_seleccionado_nombre = nombre
        print(f"{nombre} seleccionado como portero")
        messagebox.showinfo("Portero seleccionado", f"{nombre}")

        # Guardar selección del equipo
        if self.jugador_seleccionado_nombre and self.portero_seleccionado_nombre:
            if equipo_actual == 1:
                equipos_seleccionados["equipo1"] = {
                    "jugador": self.jugador_seleccionado_nombre,
                    "portero": self.portero_seleccionado_nombre
                }
                equipo_actual = 2
                messagebox.showinfo("Equipo 1 listo", "Selecciona el segundo equipo")
            elif equipo_actual == 2:
                equipos_seleccionados["equipo2"] = {
                    "jugador": self.jugador_seleccionado_nombre,
                    "portero": self.portero_seleccionado_nombre
                }
                messagebox.showinfo("Equipos listos", "¡Ambos equipos están listos! Iniciando juego...")
                print(equipos_seleccionados)
                self.iniciar_juego()

        self.cerrar_ventana()

    def cerrar_ventana(self):
        pygame.mixer.music.stop()
        if self.cap:
            self.cap.release()
        self.ventana.destroy()
        self.master.deiconify()  # Muestra la ventana principal

    def iniciar_juego(self):
        # Aquí puedes abrir tu ventana de juego real
        messagebox.showinfo("Juego", f"Comienza el partido entre:\n\n"
                            f"Equipo 1: {equipos_seleccionados['equipo1']}\n"
                            f"Equipo 2: {equipos_seleccionados['equipo2']}")

# -------------------- CLASE MENÚ PRINCIPAL --------------------
class VentanaMenu:
    def __init__(self):
        pygame.mixer.init()
        self.menu = tk.Tk()
        self.menu.title("Menú Principal")
        self.menu.geometry("850x478")

        # Fondo del menú
        self.cap = cv2.VideoCapture("fondo_futbolin1.mp4")
        self.label_fondo = tk.Label(self.menu)
        self.label_fondo.place(x=0, y=0, relwidth=1, relheight=1)
        self.actualizar_fondo()

        # Botón Play
        self.boton_play = tk.Button(self.menu, text="Play", font=("Arial", 16), bg="white", command=self.ir_a_principal)
        self.boton_play.place(x=425, y=200, anchor="center")

        # Botón About
        self.boton_about = tk.Button(self.menu, text="About", font=("Arial", 16), bg="white", command=self.About)
        self.boton_about.place(x=425, y=280, anchor="center")

    def actualizar_fondo(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (850, 478))
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.label_fondo.imgtk = imgtk
            self.label_fondo.config(image=imgtk)
        else:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.menu.after(20, self.actualizar_fondo)

    def About(self):
        about = tk.Toplevel(self.menu)
        about.title("About")
        about.geometry("500x350")
        tk.Label(about, text="Johan Jiménez Corella y Kendall Mena Arias",
                 font=("Arial", 12)).pack(pady=40)

    def ir_a_principal(self):
        self.cap.release()
        self.menu.destroy()
        app = VentanaPrincipal()
        app.ejecutar()

    def ejecutar(self):
        self.menu.mainloop()

# -------------------- CLASE PRINCIPAL --------------------
class VentanaPrincipal:
    def __init__(self):
        pygame.mixer.init()

        # Crear ventana principal
        self.ventana = tk.Tk()
        self.ventana.title("Inicio")
        self.ventana.geometry("850x478")

        # Fondo animado (video)
        self.cap = cv2.VideoCapture("fondo_futbolin1.mp4")
        self.label_fondo = tk.Label(self.ventana)
        self.label_fondo.place(x=0, y=0, relwidth=1, relheight=1)
        self.actualizar_video()
        self.rasp_control = Raspberry()
        self.rasp_control.conected()

        # Botón "About"
        self.boton_about = tk.Button(self.ventana, text="About", command=self.About, bg="white")
        self.boton_about.place(x=50, y=30, anchor="se")

        # Imagen y botón de Equipo1
        img_equipo1 = Image.open("equipo1.png").resize((150, 150))
        self.img_equipo1_tk = ImageTk.PhotoImage(img_equipo1)
        self.boton1 = tk.Button(self.ventana, image=self.img_equipo1_tk,
                                borderwidth=0, command=self.Equipo1)
        self.boton1.place(x=200, y=300, anchor="se")

        # Botón para Equipo2
        self.boton2 = tk.Button(self.ventana, text="Equipo2",
                                command=self.Equipo2, bg="white", height=20, width=20)
        self.boton2.place(x=500, y=400, anchor="se")

        # Imagen y botón de Equipo3
        img_equipo3 = Image.open("equipo3.png").resize((150, 150))
        self.img_equipo3_tk = ImageTk.PhotoImage(img_equipo3)
        self.boton3 = tk.Button(self.ventana, image=self.img_equipo3_tk, borderwidth=0, command=self.Equipo3)
        self.boton3.place(x=800, y=300, anchor="se")

    def actualizar_video(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (850, 478))
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.label_fondo.imgtk = imgtk
            self.label_fondo.config(image=imgtk)
        else:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.ventana.after(20, self.actualizar_video)

    def About(self):
        about = tk.Toplevel(self.ventana)
        about.title("About")
        about.geometry("500x350")
        tk.Label(about, text="Johan Jiménez Corella y Kendall Mena Arias",
                 font=("Arial", 12)).pack(pady=40)

    # Crear ventanas de equipos
    def Equipo1(self):
        VentanaEquipo(
            self.ventana,
            titulo="Equipo 1",
            imagenes=["pateador1_1.png", "pateador1_2.png", "pateador1_3.png"],
            nombres=["Pinkman", "Walther", "Saúl"],
            sonido="sonidoequipo1.mp3",
            video_path="fondo_equipo1.mp4",
            imagenes_porteros=["portero1_1.png", "portero1_2.png", "portero1_3.png"],
            nombres_porteros=["Huell", "Mike", "Salamanca"]
        )

    def Equipo2(self):
        VentanaEquipo(
            self.ventana,
            titulo="Equipo 2",
            imagenes=["pateador2_1.png", "pateador2_2.png", "pateador2_3.png"],
            nombres=["Jason good", "Luis Barboza", "Jugador2-3"],
            imagenes_porteros=["portero2_1.png", "portero2_2.png", "portero2_3.png"],
            nombres_porteros=["Portero2-1", "Portero2-2", "Portero2-3"]
        )

    def Equipo3(self):
        VentanaEquipo(
            self.ventana,
            titulo="Equipo 3",
            imagenes=["pateador3_1.png", "pateador3_2.png", "pateador3_3.png"],
            nombres=["Jhonny", "Ricardo", "Jordi"],
            sonido="sonidoequipo3.mp3",
            imagenes_porteros=["portero3_1.png", "portero3_2.png", "portero3_3.png"],
            nombres_porteros=["Lana", "Mia", "LilMilk"]
        )

    def ejecutar(self):
        self.ventana.mainloop()

# -------------------- EJECUCIÓN --------------------
if __name__ == "__main__":
    menu = VentanaMenu()
    menu.ejecutar()
