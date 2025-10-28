
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

    # Close the socket properly before exiting
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

    last_turn = None  # Track last turn to detect changes

    while True:
        # read switch to determine current attacking team
        cur_switch = Switch.value()
        attacking = 'red' if cur_switch == 0 else 'white'

        # Only update LEDs and send TURN message if the turn changed
        if attacking != last_turn:
            # Clear all LEDs first
            Eqp_Rojo.value(0)
            Eqp_Blanco.value(0)
            clear_blue_leds()

            # Indicate turn by lighting the respective team LED
            if attacking == 'red':
                Eqp_Rojo.value(1)
            else:
                Eqp_Blanco.value(1)

            # Update last turn and notify client
            last_turn = attacking
            try:
                conn.send(f"TURN:{attacking.upper()}".encode())
                print(f"Turn changed to: {attacking}")
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

        # determine goalkeeper and goal detection
        gk = gk_positions.get(attacking)

        # If no goalkeeper is set, randomly assign one for this turn
        if gk is None:
            import random
            gk = random.randint(1, 6)  # Random position 1-6
            gk_positions[attacking] = gk
            print(f"Randomly placed goalkeeper at position {gk}")

        # Check if the pressed button matches goalkeeper position
        blocked = pressed_idx == gk

        if blocked:
            # Goalkeeper blocks -> more dramatic block effect
            print(
                f"¡ATAJADA! El portero del equipo {attacking} en posición {gk} atajó el tiro del botón {pressed_idx}")

            # First phase: Quick flash of blocked position
            for _ in range(3):
                blue_leds[gk-1].value(1)  # Light up goalkeeper position
                time.sleep(0.1)
                blue_leds[gk-1].value(0)
                time.sleep(0.1)

            # Second phase: Sweep effect from goalkeeper position
            for _ in range(2):
                # Light up from goalkeeper to both sides
                left = gk-1
                right = gk-1
                blue_leds[gk-1].value(1)
                time.sleep(0.1)

                while left > 0 or right < len(blue_leds)-1:
                    if left > 0:
                        left -= 1
                        blue_leds[left].value(1)
                    if right < len(blue_leds)-1:
                        right += 1
                        blue_leds[right].value(1)
                    time.sleep(0.05)

                time.sleep(0.2)
                clear_blue_leds()

            try:
                conn.send(
                    f"NO_GOAL:{attacking.upper()}:{pressed_idx}".encode())
            except Exception as e:
                print("Error sending NO_GOAL", e)
            print("BLOCK: goalkeeper present at", gk)

            # Restore turn LED
            if attacking == 'red':
                Eqp_Rojo.value(1)
            else:
                Eqp_Blanco.value(1)

        else:
            # Goal celebration -> super dramatic LED sequence
            print(f"¡GOL! Equipo {attacking} anotó con el botón {pressed_idx}")

            # First phase: Wave effect
            for _ in range(3):
                # Forward wave
                for i in range(len(blue_leds)):
                    blue_leds[i].value(1)
                    time.sleep(0.05)
                # Reverse wave
                for i in range(len(blue_leds)-1, -1, -1):
                    blue_leds[i].value(0)
                    time.sleep(0.05)

            # Second phase: Flash all LEDs rapidly
            for _ in range(6):
                # All on
                for led in blue_leds:
                    led.value(1)
                if attacking == 'red':
                    Eqp_Rojo.value(1)
                else:
                    Eqp_Blanco.value(1)
                time.sleep(0.15)

                # All off
                for led in blue_leds:
                    led.value(0)
                Eqp_Rojo.value(0)
                Eqp_Blanco.value(0)
                time.sleep(0.1)

            try:
                conn.send(f"GOAL:{attacking.upper()}:{pressed_idx}".encode())
            except Exception as e:
                print("Error sending GOAL", e)

            print("GOAL for", attacking)
            # Turn off all LEDs after celebration
            Eqp_Rojo.value(0)
            Eqp_Blanco.value(0)
            clear_blue_leds()

        # After goal/block, wait for switch change to continue
        print("Esperando cambio de switch para continuar")
        cur = Switch.value()

        # Small delay to avoid bounce
        time.sleep(0.1)

        # Wait for switch change
        while Switch.value() == cur:
            time.sleep(0.05)

        print("Switch cambió, cambiando turno al otro equipo")

        # Let the next loop iteration handle the LED changes


if __name__ == '__main__':
    ip = connect_wifi()
    start_server(ip)
