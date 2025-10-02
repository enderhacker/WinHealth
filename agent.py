#!/usr/bin/env python3
"""
agent.py (Fixed and Optimized)
Agent para LAN que:
 - Emite broadcast UDP periódicos con host/port.
 - Escucha conexiones TCP en TCP_PORT.
 - Protocolo simple:
    * Cliente conecta, envía TOKEN\n
    * Agent responde AUTH_OK\n o AUTH_FAIL\n
    * Cliente envía "SHELL\n" para iniciar sesión interactiva (a partir de ese punto
      todo el socket se usa como stream entre PTY <-> socket).
    * O cliente envía "CMD\n" seguida de una línea JSON con {"cmd":"popup","args":{...}}
      Agent ejecuta comando puntual y responde una línea JSON con {"ok":true,"msg":"..."}
 - Implementa popup en Windows mediante VBS temporal.
 - Asegura limpieza al cerrar shell.
"""
import asyncio
import socket
import os
import json
import base64
import pyautogui
import tempfile
import subprocess
import getpass
import threading

TCP_PORT = 56700
UDP_BROADCAST_PORT = 56701
BROADCAST_INTERVAL = 5
SHARED_TOKEN = "gmhMWfvT0P4RPKgrpYMtYBViXPg8.Tj57Gf0UQJzDlqOQGa0pO5o-Ptj9tYGUFZlQGRuHsX4g4O0Gj8Mjç+O2BKiF3KXZwzKXdRy2rHd€@9zJwGEyOiO2yGP51KoKdDHIOfSCE"

HOSTNAME = socket.gethostname()


# ----------------- UDP broadcaster -----------------
async def udp_broadcaster():
    msg = json.dumps({"host": HOSTNAME, "port": TCP_PORT}).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while True:
        try:
            sock.sendto(msg, ("255.255.255.255", UDP_BROADCAST_PORT))
        except Exception as e:
            print(f"[UDP] Error en broadcast: {e}")
        await asyncio.sleep(BROADCAST_INTERVAL)


# ----------------- Helper: execute popup -----------------
import tempfile, subprocess, threading, os


import tempfile
import subprocess
import threading
import os


def do_popup_windows(text, title="Aviso", type_="info"):
    """
    Muestra un popup topmost en Windows usando VBScript.
    type_ puede ser: "info", "warning", "error"
    """
    try:
        safe_text = text.replace('"', "'")
        safe_title = title.replace('"', "'")

        # Mapeo de iconos
        type_map = {
            "info": 64,
            "warning": 48,
            "error": 16,
        }  # vbInformation, vbExclamation, vbCritical
        icon_val = type_map.get(type_.lower(), 64)

        vbs_code = f"""
msgText = "{safe_text}"
msgTitle = "{safe_title}"
' Valores: 0 = OK only, {icon_val} = icono, 4096 = siempre arriba
MsgBox msgText, 0 + {icon_val} + 4096, msgTitle
"""

        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".vbs", mode="w", encoding="utf-8"
        )
        tmp.write(vbs_code)
        tmp.close()

        def run_and_delete():
            subprocess.run(["wscript", tmp.name], shell=False)
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)

        threading.Thread(target=run_and_delete, daemon=True).start()
        return True, "Popup lanzado correctamente"
    except Exception as e:
        try:
            if tmp and os.path.exists(tmp.name):
                os.unlink(tmp.name)
        except:
            pass
        return False, str(e)


# ----------------- TCP handler -----------------
async def handle_client(reader, writer):
    peer = writer.get_extra_info("peername")
    print(f"[+] Conexión entrante desde {peer}")

    try:
        # 1. Autenticación
        token_line = await asyncio.wait_for(reader.readline(), timeout=10.0)
        token = token_line.decode(errors="ignore").strip()

        if token != SHARED_TOKEN:
            writer.write(b"AUTH_FAIL\n")
            await writer.drain()
            print(f"[-] Auth falló para {peer}")
            return

        writer.write(b"AUTH_OK\n")
        await writer.drain()

        # 2. Leer modo (SHELL o CMD)
        header = await asyncio.wait_for(reader.readline(), timeout=10.0)
        mode = header.decode(errors="ignore").strip().upper()

        if mode == "SHELL":
            print(f"[*] Iniciando SHELL para {peer}")
            await shell_session(reader, writer)
        elif mode == "CMD":
            jline = await asyncio.wait_for(reader.readline(), timeout=10.0)
            try:
                payload = json.loads(jline.decode(errors="ignore"))
                res = await handle_command(payload)
                writer.write((json.dumps(res) + "\n").encode())
                await writer.drain()
            except json.JSONDecodeError:
                writer.write(
                    json.dumps({"ok": False, "msg": "JSON inválido"}).encode() + b"\n"
                )
                await writer.drain()
        else:
            writer.write(b"ERROR: Modo no reconocido\n")
            await writer.drain()

    except asyncio.TimeoutError:
        print(f"[-] Timeout esperando datos de {peer}")
    except ConnectionResetError:
        print(f"[*] Conexión cerrada abruptamente por {peer}")
    except Exception as e:
        print(f"[!] Error en handle_client: {e}")
    finally:
        if not writer.is_closing():
            writer.close()
            await writer.wait_closed()
        print(f"[-] Conexión finalizada con {peer}")


async def handle_command(payload):
    cmd = payload.get("cmd")
    args = payload.get("args", {})

    if cmd == "popup":
        text = args.get("text", "Mensaje")
        title = args.get("title", "Aviso")
        type_ = args.get("type", "info")

        if os.name == "nt":
            # Lanzar popup en un thread para que no bloquee
            threading.Thread(
                target=do_popup_windows, args=(text, title, type_), daemon=True
            ).start()
            return {"ok": True, "msg": "Popup lanzado en el agente"}
        else:
            return {
                "ok": False,
                "msg": "Popups solo implementados para Windows en este agente.",
            }

    elif cmd == "openx":
        target = args.get("target")
        if not target:
            return {"ok": False, "msg": "No se proporcionó 'target'"}
        try:
            if os.name == "nt":
                # `start` es un comando de shell, necesita `shell=True`
                subprocess.Popen(["start", "", target], shell=True)
            else:
                subprocess.Popen(["xdg-open", target])  # Para Linux
            return {"ok": True, "msg": f"Comando 'openx' para '{target}' lanzado."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    elif cmd == "info":
        return {
            "ok": True,
            "msg": "info",
            "data": {"host": HOSTNAME, "user": getpass.getuser(), "cwd": os.getcwd()},
        }

    else:
        return {"ok": False, "msg": "Comando desconocido"}


# ----------------- SHELL session for Windows -----------------
async def shell_session(reader, writer):
    # Iniciar cmd.exe
    proc = await asyncio.create_subprocess_exec(
        "cmd.exe",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    async def pipe_reader_to_writer(proc_reader, sock_writer):
        """Lee del proceso (stdout) y escribe en el socket."""
        while not sock_writer.is_closing() and proc.returncode is None:
            try:
                data = await proc_reader.read(4096)
                if not data:
                    break
                sock_writer.write(data)
                await sock_writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                break
            except Exception:
                break

    async def pipe_writer_to_reader(sock_reader, proc_writer):
        """Lee del socket y escribe en el proceso (stdin)."""
        while not sock_reader.at_eof() and proc.returncode is None:
            try:
                data = await sock_reader.read(4096)
                if not data:
                    break
                proc_writer.write(data)
                await proc_writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                break
            except Exception:
                break

    # Iniciar las dos tareas de "puente"
    task_stdout = asyncio.create_task(pipe_reader_to_writer(proc.stdout, writer))
    task_stdin = asyncio.create_task(pipe_writer_to_reader(reader, proc.stdin))

    # Esperar a que una de las tareas termine (lo que indica que la conexión se cerró o el proceso terminó)
    done, pending = await asyncio.wait(
        [task_stdout, task_stdin], return_when=asyncio.FIRST_COMPLETED
    )

    # Cancelar las tareas pendientes para limpiar
    for task in pending:
        task.cancel()

    # Terminar el proceso si todavía está en ejecución
    if proc.returncode is None:
        proc.terminate()
        await proc.wait()


# ----------------- TCP server -----------------
async def tcp_server():
    server = await asyncio.start_server(handle_client, host="0.0.0.0", port=TCP_PORT)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"[+] TCP escuchando en {addrs}")
    async with server:
        await server.serve_forever()


# ----------------- Main -----------------
async def main():
    await asyncio.gather(udp_broadcaster(), tcp_server())


if __name__ == "__main__":
    if os.name != "nt":
        print("Este agente está optimizado para Windows.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAgent finalizando.")
