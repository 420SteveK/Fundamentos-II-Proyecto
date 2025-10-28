import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2
import pygame
import socket
import threading
import queue
import time

message_queue = queue.Queue()

# -------------------- CLASE CONEXIÓN RASPBERRY --------------------


class Raspberry:
    def __init__(self, ip="192.168.1.226", port=1717):
        self.server_ip = ip
        self.port = port
        self.connected = False
        self.client_socket = None
        self.reconnect_tries = 0
        self.max_reconnect_tries = 3
        self.last_reconnect_time = 0
        self.reconnect_timeout = 5  # seconds between reconnection attempts
        self.receive_thread = None
        self.should_run = True  # Control flag for the receive thread

    def conected(self):
        MAX_RETRIES = 3
        retries = 0
        while retries < MAX_RETRIES and not self.connected:
            try:
                print(
                    f"Intentando conectar a Raspberry ({retries + 1}/{MAX_RETRIES})...")
                # Crear un nuevo socket en cada intento
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except:
                        pass
                self.client_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(5)  # Aumentado a 5 segundos
                self.client_socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                # Configurar TCP keepalive
                if hasattr(socket, "TCP_KEEPIDLE"):
                    self.client_socket.setsockopt(
                        socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                if hasattr(socket, "TCP_KEEPINTVL"):
                    self.client_socket.setsockopt(
                        socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
                if hasattr(socket, "TCP_KEEPCNT"):
                    self.client_socket.setsockopt(
                        socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

                self.client_socket.connect((self.server_ip, self.port))
                self.connected = True
                # Iniciar thread de recepción
                self.receive_thread = threading.Thread(
                    target=self.receive_messages,
                    daemon=True
                )
                self.receive_thread.start()
                print("¡Conectado exitosamente a Raspberry Pico W!")
                messagebox.showinfo(
                    "Conexión", "¡Conectado exitosamente a Raspberry Pico W!")
                return True
            except Exception as e:
                print(f"Error al conectar: {e}")
                retries += 1
                time.sleep(2)  # Aumentado a 2 segundos entre intentos

        if not self.connected:
            messagebox.showerror("Error de conexión",
                                 f"No se pudo conectar a la Raspberry ({self.server_ip}).\nVerifique que esté encendida y la IP sea correcta.")
        return False

    def receive_messages(self):
        while self.should_run:
            if not self.connected:
                current_time = time.time()
                if (current_time - self.last_reconnect_time) >= self.reconnect_timeout:
                    if self.reconnect_tries < self.max_reconnect_tries:
                        print(
                            f"Intento de reconexión {self.reconnect_tries + 1}/{self.max_reconnect_tries}")
                        try:
                            # Limpiar socket anterior si existe
                            if self.client_socket:
                                try:
                                    self.client_socket.close()
                                except:
                                    pass

                            # Crear nuevo socket
                            self.client_socket = socket.socket(
                                socket.AF_INET, socket.SOCK_STREAM)
                            self.client_socket.settimeout(5)
                            self.client_socket.setsockopt(
                                socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                            self.client_socket.connect(
                                (self.server_ip, self.port))
                            self.connected = True
                            self.reconnect_tries = 0
                            print("¡Reconexión exitosa!")
                        except Exception as e:
                            print(f"Error en reconexión: {e}")
                            self.reconnect_tries += 1
                        self.last_reconnect_time = current_time
                    else:
                        print("Máximo número de intentos de reconexión alcanzado")
                        time.sleep(5)  # Esperar antes de reiniciar el contador
                        self.reconnect_tries = 0
                time.sleep(1)
                continue

            try:
                if not self.client_socket:
                    self.handle_disconnect()
                    continue

                # Timeout más corto para detección rápida
                self.client_socket.settimeout(1.0)
                msg = self.client_socket.recv(1024).decode()
                if not msg:
                    raise ConnectionError("Conexión cerrada por el servidor")

                print(f"Raspberry: {msg}")
                message_queue.put(msg)

            except socket.timeout:
                # Timeout normal, continuar
                continue
            except Exception as e:
                print(f"Error en recepción: {e}")
                self.handle_disconnect()

            time.sleep(0.1)

    def handle_disconnect(self):
        """Maneja la desconexión del servidor"""
        self.connected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.client_socket = None
        self.reconnect_tries = 0  # Resetear contador de intentos
        self.last_reconnect_time = time.time()  # Actualizar tiempo del último intento
        print("Desconectado del servidor - Preparando reconexión")

    def close(self):
        """Cierra la conexión de forma limpia"""
        self.should_run = False  # Detener el thread de recepción
        self.connected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.client_socket = None
        # Esperar a que el thread termine
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)


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
        self.portero_seleccionado_idx = None

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
        try:
            if not hasattr(self, 'ventana') or not self.cap:
                return

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

            if hasattr(self, 'ventana') and self.ventana.winfo_exists():
                # store after id so it can be cancelled on close
                try:
                    self._after_id = self.ventana.after(
                        20, self.actualizar_fondo)
                except Exception:
                    # fallback to scheduling without storing
                    self.ventana.after(20, self.actualizar_fondo)
        except Exception as e:
            print(f"Error en actualizar_fondo: {e}")
            # Intentar reprogramar el siguiente frame si aún existe la ventana
            if hasattr(self, 'ventana') and self.ventana.winfo_exists():
                try:
                    self._after_id = self.ventana.after(
                        20, self.actualizar_fondo)
                except Exception:
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
        # Use after to schedule messagebox from main thread
        self.ventana.after(0, lambda: messagebox.showinfo(
            "Jugador seleccionado", f"{nombre}"))

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
            # include index i so we know which portero was selected
            tk.Button(
                self.ventana,
                image=img,
                borderwidth=0,
                command=lambda n=nombre, idx=i: self.portero_seleccionado(
                    n, idx)
            ).place(x=x, y=y, anchor="se")

    def portero_seleccionado(self, nombre, idx):
        global equipo_actual, rasp_control_interface
        self.portero_seleccionado_nombre = nombre
        self.portero_seleccionado_idx = idx
        print(f"{nombre} seleccionado como portero")
        self.ventana.after(0, lambda: messagebox.showinfo(
            "Portero seleccionado", f"{nombre}"))

        # Guardar selección del equipo
        if self.jugador_seleccionado_nombre and self.portero_seleccionado_nombre:
            if equipo_actual == 1:
                equipos_seleccionados["equipo1"] = {
                    "jugador": self.jugador_seleccionado_nombre,
                    "portero": self.portero_seleccionado_nombre,
                    "portero_idx": self.portero_seleccionado_idx
                }
                equipo_actual = 2
                self.ventana.after(0, lambda: messagebox.showinfo(
                    "Equipo 1 listo", "Selecciona el segundo equipo"))
            elif equipo_actual == 2:
                equipos_seleccionados["equipo2"] = {
                    "jugador": self.jugador_seleccionado_nombre,
                    "portero": self.portero_seleccionado_nombre,
                    "portero_idx": self.portero_seleccionado_idx
                }
                # Schedule messagebox on main thread
                self.ventana.after(0, lambda: messagebox.showinfo(
                    "Equipos listos", "¡Ambos equipos están listos! Iniciando juego..."))
                print(equipos_seleccionados)
                # Send goalkeeper positions to Raspberry and start selection
                try:
                    # Map logical portero indexes to physical button numbers:
                    # team1 portero indices 0..2 -> physical 1..3
                    # team2 portero indices 0..2 -> physical 4..6
                    gk1 = equipos_seleccionados['equipo1']['portero_idx'] + 1
                    gk2 = equipos_seleccionados['equipo2']['portero_idx'] + 4
                    msg = f"GK_POS:{gk1},{gk2}"
                    # Use global rasp_control_interface if available
                    if 'rasp_control_interface' in globals() and rasp_control_interface.connected:
                        rasp_control_interface.client_socket.send(msg.encode())
                        # small delay then send start command
                        rasp_control_interface.client_socket.send(
                            b"START_SELECTION")
                    else:
                        print("Raspberry not connected; cannot send GK_POS/START")
                except Exception as e:
                    print("Error sending GK_POS/START to Raspberry:", e)
                # The Raspberry will read the potentiometer and reply with EQUIPO_SELECCIONADO.
                # The GUI will open the game window when it receives that message.

        self.cerrar_ventana()

    def cerrar_ventana(self):
        pygame.mixer.music.stop()
        if self.cap:
            self.cap.release()
        # cancel scheduled after callback if present
        try:
            if hasattr(self, '_after_id') and self._after_id:
                try:
                    self.ventana.after_cancel(self._after_id)
                except Exception:
                    pass
        except Exception:
            pass
        self.ventana.destroy()
        self.master.deiconify()  # Muestra la ventana principal

    def iniciar_juego(self):
        global rasp_control_interface
        if not rasp_control_interface or not rasp_control_interface.connected:
            messagebox.showerror(
                "Error", "No hay conexión con la Raspberry Pi")
            return

        try:
            rasp_control_interface.client_socket.send(
                "START_SELECTION".encode())
            print("Enviado START_SELECTION a Raspberry")
        except Exception as e:
            print(f"Error enviando START_SELECTION: {e}")
            messagebox.showerror(
                "Error", "Error al comunicarse con la Raspberry Pi")
            return

        # Show progress window for 5 seconds
        seleccion = tk.Toplevel(self.ventana)
        seleccion.title("Selección de Equipos")
        seleccion.geometry("400x200")

        label = tk.Label(seleccion, text="Girando el potenciómetro para seleccionar equipos...\n"
                         "Por favor espere 5 segundos.", font=("Arial", 12))
        label.pack(pady=20)

        progress = tk.ttk.Progressbar(
            seleccion, length=300, mode='determinate')
        progress.pack(pady=20)

        def update_progress(count):
            progress['value'] = count * 20  # 5 seconds = 100%
            if count < 5:
                seleccion.after(1000, lambda: update_progress(count + 1))
            else:
                seleccion.destroy()

        update_progress(0)

# -------------------- CLASE MENÚ PRINCIPAL --------------------
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
        self.boton_play = tk.Button(self.menu, text="Play", font=(
            "Arial", 16), bg="white", command=self.ir_a_principal)
        self.boton_play.place(x=425, y=200, anchor="center")

        # Botón About
        self.boton_about = tk.Button(self.menu, text="About", font=(
            "Arial", 12), bg="white", command=self.About)
        self.boton_about.place(x=25, y=20, anchor="center")

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
        try:
            self._after_id = self.menu.after(20, self.actualizar_fondo)
        except Exception:
            self.menu.after(20, self.actualizar_fondo)

    def About(self):
        about = tk.Toplevel(self.menu)
        about.title("Acerca del Autor")
        about.geometry("600x500")

        # === Fondo de la ventana About ===
        try:
            fondo = Image.open("fondocielo.jpg")
            fondo = fondo.resize((600, 500))
            fondo_img = ImageTk.PhotoImage(fondo)
            label_fondo = tk.Label(about, image=fondo_img)
            label_fondo.place(x=0, y=0, relwidth=1, relheight=1)
            label_fondo.lower()  # 🔹 Envía el fondo detrás de todo
            about.fondo_img = fondo_img
        except:
            about.configure(bg="lightblue")

        # === Botón Cerrar en la esquina superior derecha ===
        boton_cerrar = tk.Button(
            about, text="atrás", command=about.destroy,
            font=("Arial", 10, "bold"), bg="lightgray", fg="black", width=3
        )
        # 🔹 Posición en esquina superior derecha
        boton_cerrar.place(x=20, y=10)

        tk.Label(about, text="Información del Proyecto",
                 font=("Arial", 16, "bold")).pack(pady=10)
        try:
            imagen = Image.open("image_About.jpg")
            imagen = imagen.resize((250, 200))
            img = ImageTk.PhotoImage(imagen)
            tk.Label(about, image=img).pack(pady=5)
            about.img = img
        except:
            tk.Label(about, text="[Foto del Autor Aquí]",
                     font=("Arial", 12, "italic")).pack(pady=5)

        marco = tk.Frame(about, bg="sky blue")
        marco.pack(pady=10, fill="both", expand=True, padx=20)

        datos = [
            ("Autores:", "Johan Jiménez Corella y Kendall Mena Arias"),
            ("Identificación:", "2025080849,     2025095924"),
            ("Asignatura:", "Fundamentos de sistemas computacionales "),
            ("Carrera:", "Computadores(CE)"),
            ("Año:", "2025"),
            ("Profesor:", "Luis Barboza"),
            ("País de Producción:", "Costa Rica"),
        ]

        for etiqueta, valor in datos:
            contenedor = tk.Frame(marco, bg="black")
            contenedor.pack(anchor="w", pady=3)
            tk.Label(contenedor, text=etiqueta, font=(
                "Arial", 12, "bold"), bg="sky blue").pack(side="left")
            tk.Label(contenedor, text=valor, font=("Arial", 12),
                     bg="sky blue").pack(side="left", padx=5)

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

        # Establecer conexión con Raspberry primero
        self.rasp_control = Raspberry()
        if not self.rasp_control.conected():
            # Si no hay conexión, mostrar botón de reintentar
            self.retry_button = tk.Button(self.ventana, text="Reintentar Conexión",
                                          command=self.retry_connection,
                                          font=("Arial", 12), bg="yellow")
            self.retry_button.place(x=425, y=30, anchor="center")

        # Fondo animado (video)
        self.cap = cv2.VideoCapture("fondo_futbolin1.mp4")
        self.label_fondo = tk.Label(self.ventana)
        self.label_fondo.place(x=0, y=0, relwidth=1, relheight=1)
        self.actualizar_video()

        # expose Raspberry instance globally for VentanaEquipo to send messages
        global rasp_control_interface
        rasp_control_interface = self.rasp_control

        # Scores
        self.score_red = 0
        self.score_white = 0
        self.score_label_red = tk.Label(
            self.ventana, text="Rojo: 0", font=("Arial", 12), bg="white")
        self.score_label_red.place(x=700, y=30, anchor="ne")
        self.score_label_white = tk.Label(
            self.ventana, text="Blanco: 0", font=("Arial", 12), bg="white")
        self.score_label_white.place(x=700, y=60, anchor="ne")

        # Game window state
        self.game_window = None
        self.turn_label = None
        self.turn_indicator = None
        self.pateador_label = None
        self.goleador_label = None
        # goleadores persistence file
        self.goleadores_file = "goleadores.json"
        self.goleadores = {}
        try:
            import json
            with open(self.goleadores_file, "r", encoding="utf-8") as f:
                self.goleadores = json.load(f)
        except Exception:
            self.goleadores = {}

        # start polling incoming messages from Raspberry
        self.ventana.after(200, self.check_messages)

        # Imagen y botón de Equipo1
        img_equipo1 = Image.open("equipo1.png").resize((150, 150))
        self.img_equipo1_tk = ImageTk.PhotoImage(img_equipo1)
        self.boton1 = tk.Button(self.ventana, image=self.img_equipo1_tk,
                                borderwidth=0, command=self.Equipo1)
        self.boton1.place(x=200, y=300, anchor="se")

        # Botón para Equipo2
        img_equipo2 = Image.open("equipo2.png").resize((150, 150))
        self.img_equipo2_tk = ImageTk.PhotoImage(img_equipo2)
        self.boton2 = tk.Button(self.ventana,
                                image=self.img_equipo2_tk,
                                borderwidth=0, command=self.Equipo2)

        self.boton2.place(x=500, y=300, anchor="se")
        # Imagen y botón de Equipo3
        img_equipo3 = Image.open("equipo3.png").resize((150, 150))
        self.img_equipo3_tk = ImageTk.PhotoImage(img_equipo3)
        self.boton3 = tk.Button(
            self.ventana, image=self.img_equipo3_tk, borderwidth=0, command=self.Equipo3)
        self.boton3.place(x=800, y=300, anchor="se")

    def actualizar_video(self):
        if not hasattr(self, 'ventana'):
            return
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
        self._after_id = self.ventana.after(10, self.actualizar_video)

    # Crear ventanas de equipos

    def Equipo1(self):
        VentanaEquipo(
            self.ventana,
            titulo="Equipo 1",
            imagenes=["pateador1_1.png", "pateador1_2.png", "pateador1_3.png"],
            nombres=["Pinkman", "Walther", "Saúl"],
            sonido="sonidoequipo1.mp3",
            video_path="fondo_equipo1.mp4",
            imagenes_porteros=["portero1_1.png",
                               "portero1_2.png", "portero1_3.png"],
            nombres_porteros=["Huell", "Mike", "Salamanca"]
        )

    def Equipo2(self):
        VentanaEquipo(
            self.ventana,
            titulo="Dragon ball",
            imagenes=["pateador2_1.png", "pateador2_2.png", "pateador2_3.png"],
            nombres=["Goku", "Vegueta", "Broly"],
            sonido="sonidoequipo2.mp3",
            video_path="fondo_equipo2.mp4",
            imagenes_porteros=["portero2_1.png",
                               "portero2_2.png", "portero2_3.png"],
            nombres_porteros=["Maestro Roshi", "Majin buu", "Krillin"]
        )

    def Equipo3(self):
        VentanaEquipo(
            self.ventana,
            titulo="Equipo 3",
            imagenes=["pateador3_1.png", "pateador3_2.png", "pateador3_3.png"],
            nombres=["Jhonny", "Ricardo", "Jordi"],
            sonido="sonidoequipo3.mp3",
            video_path="fondo_equipo3.mp4",
            imagenes_porteros=["portero3_1.png",
                               "portero3_2.png", "portero3_3.png"],
            nombres_porteros=["Lana", "Mia", "LilMilk"]
        )

    def ejecutar(self):
        self.ventana.mainloop()

    def retry_connection(self):
        """Maneja el intento de reconexión desde el botón de la interfaz"""
        self.rasp_control.reconnect_tries = 0  # Resetear contador de intentos
        if self.rasp_control.conected():
            self.retry_button.destroy()
            self.ventana.after(0, lambda: messagebox.showinfo("Conexión Exitosa",
                                                              "¡Conectado a Raspberry Pico W!"))

    def check_messages(self):
        try:
            while not message_queue.empty():
                msg = message_queue.get()
                print(f"Message from queue: {msg}")

                if msg.startswith("EQUIPO_SELECCIONADO:"):
                    try:
                        equipo = int(msg.split(":")[1])
                        print(
                            f"Equipo seleccionado por potenciómetro: {equipo}")
                        if equipo == 1:
                            self.ventana.after(0, self.Equipo1)
                        elif equipo == 2:
                            self.ventana.after(0, self.Equipo2)
                        elif equipo == 3:
                            self.ventana.after(0, self.Equipo3)
                    except ValueError as e:
                        print(f"Error procesando EQUIPO_SELECCIONADO: {e}")

                elif msg.startswith("GOAL:") or msg.startswith("NO_GOAL:"):
                    parts = msg.split(":")
                    team = parts[1]
                    button = parts[2]
                    if msg.startswith("GOAL:"):
                        if team == "RED":
                            self.score_red += 1
                            self.score_label_red.config(
                                text=f"Rojo: {self.score_red}")
                        else:
                            self.score_white += 1
                            self.score_label_white.config(
                                text=f"Blanco: {self.score_white}")
        except Exception as e:
            print(f"Error en check_messages: {e}")

        self.ventana.after(200, self.check_messages)
        try:
            self.ventana.after(200, self.check_messages)
        except Exception:
            pass


def map_adc_to_team(value):
    """
    Map ADC value (0..65535) to team according to explicit ranges:
      352 - 22081  -> Equipo 1
      22082 - 43807 -> Equipo 2
      43808 - 65535 -> Equipo 3

    Values below 352 will be treated as 352. Values above 65535 as 65535.
    """
    try:
        v = int(value)
    except Exception:
        v = 0

    # clamp
    if v < 352:
        v = 352
    if v > 65535:
        v = 65535

    if v <= 22081:
        return 1
    elif v <= 43807:
        return 2
    else:
        return 3


# -------------------- EJECUCIÓN --------------------
if __name__ == "__main__":
    menu = VentanaMenu()
    menu.ejecutar()
