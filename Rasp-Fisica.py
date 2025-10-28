
import network
import socket
import time
from machine import Pin, ADC

# WiFi credentials (adjust as needed)
SSID = "FMA"
PASSWORD = "Men@Rias2015"

# Output pins
Eqp_Rojo = Pin(0, Pin.OUT)
Led_Azl1 = Pin(1, Pin.OUT)
Led_Azl2 = Pin(2, Pin.OUT)
Led_Azl3 = Pin(3, Pin.OUT)
Led_Azl4 = Pin(4, Pin.OUT)
Led_Azl5 = Pin(5, Pin.OUT)
Led_Azl6 = Pin(6, Pin.OUT)
Eqp_Blanco = Pin(7, Pin.OUT)

# Inputs
Switch = Pin(8, Pin.IN)
Btn_Arq1 = Pin(9, Pin.IN, Pin.PULL_DOWN)
Btn_Arq2 = Pin(10, Pin.IN, Pin.PULL_DOWN)
Btn_Arq3 = Pin(11, Pin.IN, Pin.PULL_DOWN)
Btn_Arq4 = Pin(12, Pin.IN, Pin.PULL_DOWN)
Btn_Arq5 = Pin(13, Pin.IN, Pin.PULL_DOWN)
Btn_Arq6 = Pin(14, Pin.IN, Pin.PULL_DOWN)
pot = ADC(27)

# helper lists
blue_leds = [Led_Azl1, Led_Azl2, Led_Azl3, Led_Azl4, Led_Azl5, Led_Azl6]
buttons = [Btn_Arq1, Btn_Arq2, Btn_Arq3, Btn_Arq4, Btn_Arq5, Btn_Arq6]


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Desconectar si ya está conectado
    if wlan.isconnected():
        print("Desconectando de conexión anterior...")
        wlan.disconnect()
        time.sleep(1)

    print(f"Intentando conectar a red: {SSID}")
    wlan.connect(SSID, PASSWORD)

    # Esperar conexión con timeout
    max_wait = 20
    while max_wait > 0 and not wlan.isconnected():
        print("Esperando conexión... ", max_wait)
        time.sleep(1)
        max_wait -= 1

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"\n¡Conectado! IP: {ip}")
        print("Información completa:", wlan.ifconfig())
        return ip
    else:
        print("\nNo se pudo conectar al WiFi")
        return None


def map_adc_to_team(value, vmin=352, vmax=65533):
    # Clamp
    if value < vmin:
        value = vmin
    if value > vmax:
        value = vmax
    span = vmax - vmin + 1
    per = span // 3
    if value < vmin + per:
        return 1
    elif value < vmin + 2 * per:
        return 2
    else:
        return 3


def start_server(server_ip):
    print("\nIniciando servidor...")
    s = socket.socket()
    gk_positions = {"red": None, "white": None}  # physical button number 1..6

    try:
        # Permitir reusar la dirección/puerto
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        print(f"Intentando vincular al puerto 1717 en {server_ip}")
        s.bind((server_ip, 1717))
        s.listen(1)
        print("\n¡Servidor listo! Esperando conexión del cliente...")
        print(f"Dirección del servidor: {server_ip}:1717")

        conn, addr = s.accept()
        print("\n¡Cliente conectado desde:", addr)

        while True:
            data = conn.recv(2048)
            if not data:
                print("Cliente desconectado")
                break
            msg = data.decode().strip()
            print("Mensaje recibido:", msg)

            if msg.startswith("GK_POS:"):
                # format GK_POS:x,y  where x and y are physical positions 1..6
                try:
                    parts = msg.split(":", 1)[1]
                    a, b = parts.split(",")
                    gk_positions["red"] = int(a)
                    gk_positions["white"] = int(b)
                    print("Goalkeepers set -> red:%s white:%s" % (a, b))
                    conn.send("GK_OK".encode())
                except Exception as e:
                    print("GK_POS parse error", e)
                    conn.send("GK_ERR".encode())

            elif msg == "START_SELECTION":
                # Wait 5 seconds then read potentiometer and choose team
                print("START_SELECTION: esperando 5s antes de leer ADC")
                for _ in range(5):
                    time.sleep(1)
                try:
                    val = pot.read_u16()  # 0..65535
                except Exception:
                    val = pot.read() if hasattr(pot, 'read') else 0
                team = map_adc_to_team(val)
                reply = "EQUIPO_SELECCIONADO:{}".format(team)
                print("ADC value:", val, "-> team", team)
                try:
                    conn.send(reply.encode())
                except Exception as e:
                    print("Error enviando equipo seleccionado:", e)

                print("Entrando en bucle de juego")
                game_loop(conn, gk_positions)
                break
            else:
                conn.send(f"Echo: {msg}".encode())

    except Exception as e:
        print(f"Error en el servidor: {e}")
    finally:
        try:
            conn.close()
        except:
            pass
        s.close()

    gk_positions = {"red": None, "white": None}  # physical button number 1..6

    try:
        while True:
            data = conn.recv(2048)
            if not data:
                print("Cliente desconectado")
                break
            msg = data.decode().strip()
            print("Mensaje recibido:", msg)

            if msg.startswith("GK_POS:"):
                # format GK_POS:x,y  where x and y are physical positions 1..6
                try:
                    parts = msg.split(":", 1)[1]
                    a, b = parts.split(",")
                    gk_positions["red"] = int(a)
                    gk_positions["white"] = int(b)
                    print("Goalkeepers set -> red:%s white:%s" % (a, b))
                    conn.send("GK_OK".encode())
                except Exception as e:
                    print("GK_POS parse error", e)
                    conn.send("GK_ERR".encode())

            elif msg == "START_SELECTION":
                # Wait 5 seconds then read potentiometer and choose team
                print("START_SELECTION: esperando 5s antes de leer ADC")
                for i in range(5):
                    time.sleep(1)
                try:
                    val = pot.read_u16()  # 0..65535
                except Exception:
                    # fallback to read if method differs
                    val = pot.read() if hasattr(pot, 'read') else 0
                team = map_adc_to_team(val)
                reply = "EQUIPO_SELECCIONADO:{}".format(team)
                print("ADC value:", val, "-> team", team)
                try:
                    conn.send(reply.encode())
                except Exception as e:
                    print("Error enviando equipo seleccionado:", e)

                # Now start game loop (blocking until client disconnect)
                print("Entrando en bucle de juego")
                game_loop(conn, gk_positions)
                # if game_loop returns, break
                break
            else:
                # simple echo for debugging
                conn.send(f"Echo: {msg}".encode())

    finally:
        try:
            conn.close()
        except:
            pass


def clear_blue_leds():
    for led in blue_leds:
        led.value(0)


def set_blue_leds(count):
    # count: number of blue leds to turn on from start (1..6)
    clear_blue_leds()
    for i in range(min(count, len(blue_leds))):
        blue_leds[i].value(1)


def game_loop(conn, gk_positions):
    # gk_positions: dict with 'red' and 'white' physical indexes (1..6)
    prev_switch = Switch.value()
    print("gk_positions at start of game:", gk_positions)

    while True:
        # read switch to determine current attacking team
        cur_switch = Switch.value()
        attacking = 'red' if cur_switch == 0 else 'white'

        # Indicate turn by lighting the respective team LED and notify client
        if attacking == 'red':
            Eqp_Rojo.value(1)
            Eqp_Blanco.value(0)
        else:
            Eqp_Blanco.value(1)
            Eqp_Rojo.value(0)

        try:
            conn.send(f"TURN:{attacking.upper()}".encode())
        except Exception as e:
            print("Error sending TURN message", e)

        # wait for any button press
        pressed_idx = None
        while True:
            for idx, btn in enumerate(buttons, start=1):
                if btn.value() == 1:
                    pressed_idx = idx
                    break
            if pressed_idx is not None:
                break
            time.sleep(0.02)

        # collect presses during a small window (e.g., 300ms)
        presses = set()
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < 400:
            for idx, btn in enumerate(buttons, start=1):
                if btn.value() == 1:
                    presses.add(idx)
            time.sleep(0.02)

        print("Presses detected:", presses, "attacking:", attacking)

        # determine goalkeeper for attacking side
        gk = gk_positions.get(attacking)
        blocked = (gk is not None) and (gk in presses)

        if blocked:
            # goalkeeper blocks -> first 3 blue leds on
            set_blue_leds(3)
            Eqp_Rojo.value(0)
            Eqp_Blanco.value(0)
            try:
                conn.send(f"NO_GOAL:{attacking.upper()}".encode())
            except Exception as e:
                print("Error sending NO_GOAL", e)
            print("BLOCK: goalkeeper present at", gk)
            # leave LEDs on briefly
            time.sleep(2)
            clear_blue_leds()

        else:
            # goal -> all blue leds + team LED
            set_blue_leds(6)
            if attacking == 'red':
                Eqp_Rojo.value(1)
                Eqp_Blanco.value(0)
            else:
                Eqp_Blanco.value(1)
                Eqp_Rojo.value(0)

            try:
                conn.send(f"GOAL:{attacking.upper()}".encode())
            except Exception as e:
                print("Error sending GOAL", e)

            print("GOAL for", attacking)
            time.sleep(2)

            # turn off team leds and blues
            Eqp_Rojo.value(0)
            Eqp_Blanco.value(0)
            clear_blue_leds()

        # Wait until switch flips (team change) before allowing next event
        print("Esperando cambio de switch para continuar")
        cur = Switch.value()
        while Switch.value() == cur:
            time.sleep(0.05)
        print("Switch cambió, continuando")


if __name__ == '__main__':
    ip = connect_wifi()
    start_server(ip)
