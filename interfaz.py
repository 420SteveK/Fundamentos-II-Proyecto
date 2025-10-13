import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2
import pygame
class VentanaEquipo:
    def __init__(self, master, titulo, imagenes, nombres, sonido=None, video_path=None,
                 imagenes_porteros=None, nombres_porteros=None):
        self.master = master
        self.titulo = titulo
        self.imagenes = imagenes
        self.nombres = nombres
        self.sonido = sonido
        self.video_path = video_path
        self.imagenes_porteros = imagenes_porteros or []
        self.nombres_porteros = nombres_porteros or []

        self.master.withdraw()  # Oculta la ventana principal

        # Crear la ventana del equipo
        self.ventana = tk.Toplevel(master)
        self.ventana.title(self.titulo)
        self.ventana.geometry("850x478")

        # Reproducir sonido si existe
        if self.sonido:
            pygame.mixer.music.load(self.sonido)
            pygame.mixer.music.play()

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
        print(f"{nombre} seleccionado")
        messagebox.showinfo("Jugador seleccionado", f"{nombre}")

        # Mostrar porteros tras seleccionar jugador
        if self.imagenes_porteros and self.nombres_porteros:
            self.mostrar_jugadores(self.imagenes_porteros, self.nombres_porteros)

    def cerrar_ventana(self):
        pygame.mixer.music.stop()
        if self.cap:
            self.cap.release()
        self.ventana.destroy()
        self.master.deiconify()  # Muestra la ventana principal


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
            nombres=["Jugador2-1", "Jugador2-2", "Jugador2-3"],
            imagenes_porteros=["portero2_1.png", "portero2_2.png", "portero2_3.png"],
            nombres_porteros=["Portero2-1", "Portero2-2", "Portero2-3"]
        )

    def Equipo3(self):
        VentanaEquipo(
            self.ventana,
            titulo="Equipo 3",
            imagenes=["pateador3_1.png", "pateador3_2.png", "pateador3_3.png"],
            nombres=["Jugador3-1", "Jugador3-2", "Jugador3-3"],
            imagenes_porteros=["portero3_1.png", "portero3_2.png", "portero3_3.png"],
            nombres_porteros=["Portero3-1", "Portero3-2", "Portero3-3"]
        )

    def ejecutar(self):
        self.ventana.mainloop()


if __name__ == "__main__":
    app = VentanaPrincipal()
    app.ejecutar()
