#!/usr.bin/env python3
"""
admin.py (Fixed and Optimized)
Interfaz Tkinter en español:
 - Lista nodos descubiertos vía broadcast UDP.
 - Vista detalle con botones: Abrir Shell, Enviar Popup, Abrir X (ejemplo), Desconectar.
 - Abrir Shell crea una ventana con salida en tiempo real y campo de entrada.
 - Popup usa CMD protocol: abre conexión, envía token, CMD + JSON, lee respuesta y muestra resultado.
 - Reconexión automática en shell si el agente no responde; cerrar la ventana aborta.
"""
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext, ttk
import threading, socket, json, time
import os
import base64

TCP_PORT = 56700
UDP_BROADCAST_PORT = 56701
SHARED_TOKEN = "gmhMWfvT0P4RPKgrpYMtYBViXPg8.Tj57Gf0UQJzDlqOQGa0pO5o-Ptj9tYGUFZlQGRuHsX4g4O0Gj8Mjç+O2BKiF3KXZwzKXdRy2rHd€@9zJwGEyOiO2yGP51KoKdDHIOfSCE"

agents = {}  # ip -> info


# UDP listener in background thread
def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", UDP_BROADCAST_PORT))
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            try:
                info = json.loads(data.decode())
                ip = addr[0]
                agents[ip] = info
            except json.JSONDecodeError:
                pass
        except Exception:
            pass


class AdminApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Panel de Administración de Nodos")
        self.root.geometry("520x420")
        self.frame_lista = tk.Frame(root)
        self.frame_detalle = tk.Frame(root)
        self.current_agent_ip = None
        self.current_agent_info = None

        self.build_lista()
        self.build_detalle()

        self.frame_lista.pack(fill="both", expand=True)
        # actualizar lista periódicamente
        self.root.after(1000, self.refresh_listbox)

    def build_lista(self):
        tk.Label(self.frame_lista, text="Nodos descubiertos:", font=("Arial", 14)).pack(
            pady=8
        )
        self.listbox = tk.Listbox(self.frame_lista, font=("Consolas", 12))
        self.listbox.pack(fill="both", expand=True, padx=12, pady=6)
        self.listbox.bind("<Double-1>", lambda e: self.open_selected_agent())
        btn_frame = tk.Frame(self.frame_lista)
        btn_frame.pack(pady=6)
        tk.Button(btn_frame, text="Refrescar", command=self.refresh_listbox).pack(
            side="bottom", padx=6
        )

    def build_detalle(self):
        self.lbl_info = tk.Label(
            self.frame_detalle, text="", font=("Arial", 12), justify="left"
        )
        self.lbl_info.pack(pady=10)
        btns = tk.Frame(self.frame_detalle)
        btns.pack(pady=6)
        self.btn_shell = tk.Button(btns, text="Abrir Shell", command=self.open_shell)
        self.btn_shell.pack(side="left", padx=6)
        self.btn_popup = tk.Button(btns, text="Enviar Popup", command=self.send_popup)
        self.btn_popup.pack(side="left", padx=6)
        self.btn_openx = tk.Button(btns, text="Abrir X", command=self.send_openx)
        self.btn_openx.pack(side="left", padx=6)
        self.btn_transfer = tk.Button(
            btns, text="Transferencias de archivos", command=self.open_file_transfer
        )
        self.btn_transfer.pack(side="left", padx=6)
        tk.Button(
            self.frame_detalle, text="Desconectar / Volver", command=self.back_to_list
        ).pack(pady=12)

    def refresh_listbox(self):
        selected_ip = self.get_selected_ip()
        self.listbox.delete(0, tk.END)
        sorted_agents = sorted(agents.items())
        for i, (ip, info) in enumerate(sorted_agents):
            self.listbox.insert(tk.END, f"{ip} ({info.get('host')})")
            if ip == selected_ip:
                self.listbox.selection_set(i)
        self.root.after(2000, self.refresh_listbox)

    def get_selected_ip(self):
        sel = self.listbox.curselection()
        if not sel:
            return None
        line = self.listbox.get(sel[0])
        return line.split(" ")[0]

    def open_selected_agent(self):
        ip = self.get_selected_ip()
        if not ip or ip not in agents:
            messagebox.showwarning("Atención", "Selecciona un nodo válido primero.")
            return
        info = agents[ip]
        self.current_agent_ip = ip
        self.current_agent_info = info
        self.lbl_info.config(
            text=f"IP: {ip}\nHost: {info.get('host')}\nPuerto: {info.get('port')}"
        )
        self.frame_lista.pack_forget()
        self.frame_detalle.pack(fill="both", expand=True)

    def back_to_list(self):
        self.current_agent_ip = None
        self.current_agent_info = None
        self.frame_detalle.pack_forget()
        self.frame_lista.pack(fill="both", expand=True)

    # ----------------- CMD helpers -----------------
    def send_cmd(self, ip, payload, timeout=6):
        try:
            with socket.create_connection((ip, TCP_PORT), timeout=timeout) as s:
                s_file = s.makefile("rwb")
                s_file.write((SHARED_TOKEN + "\n").encode())
                s_file.flush()
                resp = s_file.readline().decode().strip()
                if resp != "AUTH_OK":
                    return {"ok": False, "msg": "Auth fail"}
                s_file.write(b"CMD\n")
                s_file.write((json.dumps(payload) + "\n").encode())
                s_file.flush()
                line = s_file.readline().decode().strip()
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    return {"ok": False, "msg": "Respuesta inválida del agente"}
        except socket.timeout:
            return {"ok": False, "msg": "Timeout: el agente no respondió a tiempo."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def send_popup(self):
        if not self.current_agent_ip:
            messagebox.showwarning("Atención", "No hay un nodo seleccionado.")
            return

        def on_send():
            text = txt.get("1.0", "end").strip()
            title = title_entry.get().strip() or "Aviso"
            type_ = type_combo.get()
            if not text:
                messagebox.showwarning("Atención", "El mensaje no puede estar vacío.")
                return
            payload = {
                "cmd": "popup",
                "args": {"text": text, "title": title, "type": type_},
            }
            res = self.send_cmd(self.current_agent_ip, payload)
            if res.get("ok"):
                messagebox.showinfo("Éxito", res.get("msg", "Popup enviado"))
            else:
                messagebox.showerror("Error", res.get("msg", "Fallo al enviar popup"))
            popup_win.destroy()

        popup_win = tk.Toplevel()  # <-- aquí no usamos self.top
        popup_win.title("Enviar Popup")
        popup_win.geometry("400x250")
        popup_win.transient()  # opcional
        popup_win.grab_set()  # solo para enfocar dialog

        tk.Label(popup_win, text="Tipo:").pack(anchor="w", padx=10, pady=(10, 0))
        type_combo = ttk.Combobox(
            popup_win, values=["info", "warning", "error"], state="readonly"
        )
        type_combo.current(0)
        type_combo.pack(fill="x", padx=10)

        tk.Label(popup_win, text="Título:").pack(anchor="w", padx=10, pady=(10, 0))
        title_entry = tk.Entry(popup_win)
        title_entry.insert(0, "Aviso")
        title_entry.pack(fill="x", padx=10)

        tk.Label(popup_win, text="Mensaje:").pack(anchor="w", padx=10, pady=(10, 0))
        txt = tk.Text(popup_win, height=5)
        txt.insert("1.0", "Hola desde Admin")
        txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        send_btn = tk.Button(popup_win, text="Enviar", command=on_send, padx=12, pady=6)
        send_btn.pack(pady=5)

    def send_openx(self):
        if not self.current_agent_ip:
            messagebox.showwarning("Atención", "No hay un nodo seleccionado.")
            return
        target = simpledialog.askstring(
            "Abrir X", "Ruta o URL a abrir:", initialvalue="notepad.exe"
        )
        if target is None:
            return
        payload = {"cmd": "openx", "args": {"target": target}}
        res = self.send_cmd(self.current_agent_ip, payload, timeout=8)
        if res.get("ok"):
            messagebox.showinfo("Éxito", res.get("msg", "OK"))
        else:
            messagebox.showerror("Error", res.get("msg", "Fallo al ejecutar openx"))

    def populate_local_tree(self, tree, path):
        tree.delete(*tree.get_children())
        for f in os.listdir(path):
            full = os.path.join(path, f)
            is_dir = os.path.isdir(full)
            tree.insert("", "end", text=f, values=(full,), open=False)

    def populate_remote_tree(self, tree, path, ip):
        tree.delete(*tree.get_children())
        payload = {"cmd": "listdir", "args": {"path": path}}
        res = self.send_cmd(ip, payload)
        if res.get("ok"):
            for entry in res["entries"]:
                tree.insert(
                    "",
                    "end",
                    text=entry["name"],
                    values=(os.path.join(path, entry["name"]),),
                    open=False,
                )

    def open_file_transfer(self):
        if not self.current_agent_ip:
            messagebox.showwarning("Atención", "No hay un nodo seleccionado.")
            return

        win = tk.Toplevel(self.root)
        win.title("Transferencias de archivos")
        win.geometry("800x400")

        # Frames
        local_frame = tk.Frame(win)
        remote_frame = tk.Frame(win)
        local_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        remote_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        tk.Label(local_frame, text="PC Local").pack()
        tk.Label(remote_frame, text="Agente Remoto").pack()

        # Local tree
        local_tree = ttk.Treeview(local_frame)
        local_tree.pack(fill="both", expand=True)
        self.populate_local_tree(local_tree, "C:\\")

        # Remote tree
        remote_tree = ttk.Treeview(remote_frame)
        remote_tree.pack(fill="both", expand=True)
        self.populate_remote_tree(remote_tree, "C:\\", self.current_agent_ip)

        # Drag & drop: double click to send from local -> remote
        def send_to_remote(event):
            item = local_tree.selection()[0]
            path = local_tree.item(item, "values")[0]
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    data = f.read()
                data_b64 = base64.b64encode(data).decode()
                payload = {"cmd": "putfile", "args": {"path": path, "data": data_b64}}
                res = self.send_cmd(self.current_agent_ip, payload)
                if res.get("ok"):
                    messagebox.showinfo("Éxito", f"Archivo {path} enviado al agente")
                else:
                    messagebox.showerror("Error", res.get("msg", "Fallo"))

        local_tree.bind("<Double-1>", send_to_remote)

    # ----------------- Shell window -----------------
    def open_shell(self):
        if not self.current_agent_ip:
            messagebox.showwarning("Atención", "No hay un nodo seleccionado.")
            return
        ShellWindow(self.root, self.current_agent_ip)


class ShellWindow:
    def __init__(self, root, ip):
        self.ip = ip
        self.top = tk.Toplevel(root)
        self.top.title(f"Shell remota - {ip}")
        self.top.geometry("720x480")
        self.txt = scrolledtext.ScrolledText(
            self.top,
            font=("Consolas", 12),
            bg="black",
            fg="white",
            insertbackground="white",
            state="disabled",
        )
        self.txt.pack(fill="both", expand=True)
        self.entry = tk.Entry(
            self.top,
            font=("Consolas", 12),
            bg="#333",
            fg="white",
            insertbackground="white",
        )
        self.entry.pack(fill="x")
        self.entry.bind("<Return>", self.send_command)
        self.entry.focus_set()

        self.top.protocol("WM_DELETE_WINDOW", self.on_close)
        self._stop = threading.Event()
        self._conn_lock = threading.Lock()
        self._sock = None

        self._thread = threading.Thread(target=self._connection_loop, daemon=True)
        self._thread.start()

    def log(self, text):
        try:

            def _append():
                self.txt.configure(state="normal")
                self.txt.insert(tk.END, text)
                self.txt.see(tk.END)
                self.txt.configure(state="disabled")

            self.top.after(0, _append)
        except Exception:
            pass

    def _connection_loop(self):
        while not self._stop.is_set():
            s = None  # Define s outside try block for access in finally
            try:
                self.log(f"\n\n[+] Conectando a {self.ip}:{TCP_PORT}...\n\n")
                s = socket.create_connection((self.ip, TCP_PORT), timeout=8)

                # --- FIX: Remove the timeout for subsequent blocking operations ---
                s.settimeout(None)
                # ----------------------------------------------------------------

                with self._conn_lock:
                    self._sock = s

                # Use a file-like object for easier line reading
                s_file = s.makefile("rwb")
                s_file.write((SHARED_TOKEN + "\n").encode())
                s_file.flush()
                resp = s_file.readline().decode().strip()

                if resp != "AUTH_OK":
                    self.log("[-] Autenticación fallida.\n")
                    break

                s_file.write(b"SHELL\n")
                s_file.flush()

                # Bucle de recepción
                while not self._stop.is_set():
                    data = s.recv(4096)
                    if not data:
                        self.log("\n[*] Conexión cerrada por el host remoto.\n")
                        break
                    self.log(data.decode(errors="ignore"))

            except socket.timeout:
                self.log("[-] Timeout al establecer la conexión inicial.\n")
            except Exception as e:
                if not self._stop.is_set():
                    self.log(f"[-] Error de conexión: {e}\n")
            finally:
                self.close_connection()

            if not self._stop.is_set():
                self.log("[*] Reintentando en 3 segundos...\n")
                time.sleep(3)

    def send_command(self, event=None):
        line = self.entry.get() + "\n"
        self.entry.delete(0, tk.END)
        with self._conn_lock:
            if self._sock:
                try:
                    self._sock.sendall(line.encode())
                except Exception as e:
                    self.log(f"[-] Error enviando comando: {e}\n")
            else:
                self.log("[-] No conectado. No se puede enviar el comando.\n")

    def close_connection(self):
        with self._conn_lock:
            if self._sock:
                try:
                    self._sock.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    self._sock.close()
                except:
                    pass
                self._sock = None

    def on_close(self):
        self._stop.set()
        self.close_connection()
        self.top.destroy()


# ----------------- Inicialización -----------------
def start_udp_thread():
    t = threading.Thread(target=udp_listener, daemon=True)
    t.start()


if __name__ == "__main__":
    start_udp_thread()
    root = tk.Tk()
    app = AdminApp(root)
    root.mainloop()
