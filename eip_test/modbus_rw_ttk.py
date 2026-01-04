"""
modbus_rw_ttk.py
- Replace EIP/CIP Assembly explicit messaging with Modbus TCP.
- Uses pymodbus (synchronous client) to read/write PLC registers.
- UI: same behavior (poll 3 words, write 1 control word with optional pulse).

Install:
    pip install pymodbus

Notes (important):
1) Modbus addressing varies by library/device.
   In pymodbus, addresses are typically ZERO-BASED offsets (0 = first register).
   Your PLC manual may show 1-based or 40001-based notation; adjust below.

2) You must map PLC variables to Modbus addresses:
   - T->O words  (PLC->PC) : typically Holding Registers (Function 03) or Input Registers (04)
   - O->T word   (PC->PLC) : typically Holding Registers (Function 06/16)

   Edit READ_ADDR / WRITE_ADDR (and optionally UNIT_ID) to match your PLC.
"""

import tkinter as tk
from tkinter import ttk
import time
import threading

from pymodbus.client import ModbusTcpClient

# ==================== 配置区 ====================
PLC_IP = "192.168.6.6"
PLC_PORT = 502
UNIT_ID = (
    1  # Modbus Unit Identifier (slave id). Many PLCs use 1; some ignore it (0/255).
)

# ---- Address mapping (EDIT THESE) ----
# Read 3 consecutive 16-bit registers: w0, w1, w2
# If you want to read D100~D102 as Holding Registers:
#   If your device uses 0-based: READ_ADDR = 100
#   If your device uses 40001-based: READ_ADDR = 40101 (then convert to 100 when using pymodbus)
READ_ADDR = 42088
READ_COUNT = 3
READ_TABLE = "hr"  # "hr"=Holding Registers (FC03), "ir"=Input Registers (FC04)

# Write 1 x 16-bit register as control word
WRITE_ADDR = 100
WRITE_TABLE = "hr"  # usually holding registers for writable area

POLL_INTERVAL_MS = 200  # 100~300ms typical for UI
WRITE_PULSE_MS = 200
ENABLE_WRITE_PULSE = True

RECONNECT_BACKOFF_S = (1, 2, 5)
# ===============================================


class PLCMonitorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("信捷PLC 监控与控制（Modbus TCP）")
        self.root.geometry("580x480")
        self.root.configure(bg="#f0f0f0")

        tk.Label(
            root,
            text="信捷PLC 控制面板",
            font=("Microsoft YaHei", 18, "bold"),
            bg="#f0f0f0",
        ).pack(pady=15)

        frame_display = ttk.LabelFrame(root, text="实时状态", padding=15)
        frame_display.pack(fill=tk.X, padx=20, pady=10)

        self.labels = {}
        items = [
            (f"Word0 (READ @{READ_TABLE}:{READ_ADDR})", "w0"),
            (f"Word1 (READ @{READ_TABLE}:{READ_ADDR+1})", "w1"),
            (f"Word2/STATE (READ @{READ_TABLE}:{READ_ADDR+2})", "w2"),
            ("当前设备状态", "device_status"),
        ]
        for text, key in items:
            row = ttk.Frame(frame_display)
            row.pack(fill=tk.X, pady=6)
            ttk.Label(
                row, text=text + "：", width=30, font=("Microsoft YaHei", 11)
            ).pack(side=tk.LEFT)
            val_label = ttk.Label(
                row, text="---", font=("Consolas", 14), foreground="blue"
            )
            val_label.pack(side=tk.LEFT)
            self.labels[key] = val_label

        self.estop_label = ttk.Label(
            frame_display,
            text="未连接",
            font=("Microsoft YaHei", 16, "bold"),
            foreground="red",
        )
        self.estop_label.pack(pady=15)

        frame_control = ttk.LabelFrame(
            root, text="虚拟操作按钮（写 控制字寄存器）", padding=20
        )
        frame_control.pack(fill=tk.X, padx=20, pady=10)

        btn_start = tk.Button(
            frame_control,
            text="启动 (Bit0)",
            font=("Microsoft YaHei", 14, "bold"),
            bg="#4CAF50",
            fg="white",
            width=12,
            height=2,
            command=lambda: self.send_command_bit(0),
        )
        btn_start.pack(side=tk.LEFT, padx=30)

        btn_stop = tk.Button(
            frame_control,
            text="停止 (Bit1)",
            font=("Microsoft YaHei", 14, "bold"),
            bg="#FF9800",
            fg="white",
            width=12,
            height=2,
            command=lambda: self.send_command_bit(1),
        )
        btn_stop.pack(side=tk.LEFT, padx=30)

        self.status_label = ttk.Label(root, text="连接状态：未连接", foreground="red")
        self.status_label.pack(pady=10)

        # runtime state
        self.running = True
        self._client = None
        self._client_lock = threading.Lock()
        self._connected = False

        self._ctrl_word = 0

        threading.Thread(target=self._worker_loop, daemon=True).start()
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ---------------- Modbus helpers ----------------
    def _set_status(self, text: str, color: str = "black"):
        self.status_label.config(text=text, foreground=color)

    def _set_connected_ui(self, ok: bool):
        if ok:
            self._set_status("连接状态：已连接", "green")
        else:
            self._set_status("连接状态：未连接", "red")

    def _open_connection(self):
        with self._client_lock:
            try:
                if self._client is not None:
                    self._client.close()
            except Exception:
                pass
            self._client = ModbusTcpClient(host=PLC_IP, port=PLC_PORT, timeout=1.0)
            ok = self._client.connect()
            if not ok:
                self._client.close()
                self._client = None
                raise RuntimeError("ModbusTCP connect() failed")
            self._connected = True

    def _close_connection(self):
        with self._client_lock:
            try:
                if self._client is not None:
                    self._client.close()
            except Exception:
                pass
            self._client = None
            self._connected = False

    def _read_words(self):
        with self._client_lock:
            cli = self._client
        if cli is None:
            raise RuntimeError("PLC not connected")

        if READ_TABLE == "hr":
            rr = cli.read_holding_registers(
                address=READ_ADDR, count=READ_COUNT, slave=UNIT_ID
            )
        elif READ_TABLE == "ir":
            rr = cli.read_input_registers(
                address=READ_ADDR, count=READ_COUNT, slave=UNIT_ID
            )
        else:
            raise ValueError("READ_TABLE must be 'hr' or 'ir'")

        if rr.isError():
            raise RuntimeError(f"Modbus read error: {rr}")

        regs = getattr(rr, "registers", None)
        if regs is None or len(regs) < READ_COUNT:
            raise RuntimeError(f"Modbus read returned insufficient registers: {regs}")

        # regs are already 0..65535
        return regs[0], regs[1], regs[2]

    def _write_word(self, word_u16: int):
        if not (0 <= word_u16 <= 0xFFFF):
            raise ValueError("word_u16 must be 0..65535")

        with self._client_lock:
            cli = self._client
        if cli is None:
            raise RuntimeError("PLC not connected")

        if WRITE_TABLE != "hr":
            raise ValueError("WRITE_TABLE must be 'hr' for writable registers")

        wr = cli.write_register(
            address=WRITE_ADDR, value=word_u16, slave=UNIT_ID
        )  # FC06
        if wr.isError():
            raise RuntimeError(f"Modbus write error: {wr}")

    # ---------------- UI actions ----------------
    def send_command_bit(self, bit_index: int):
        if bit_index < 0 or bit_index > 15:
            self._set_status("命令位超范围(0..15)", "red")
            return

        if not self._connected:
            self._set_status("连接失败，无法发送命令", "red")
            return

        mask = 1 << bit_index
        self._ctrl_word |= mask

        try:
            self._write_word(self._ctrl_word)
            self._set_status(
                f"已发送命令：Bit{bit_index}=1 (ctrl=0x{self._ctrl_word:04X})", "blue"
            )
        except Exception as e:
            self._set_status(f"发送失败: {e}", "red")
            return

        if ENABLE_WRITE_PULSE and WRITE_PULSE_MS > 0:
            self.root.after(WRITE_PULSE_MS, lambda: self._clear_command_bit(bit_index))

    def _clear_command_bit(self, bit_index: int):
        if not self._connected:
            return
        mask = 1 << bit_index
        self._ctrl_word &= (~mask) & 0xFFFF
        try:
            self._write_word(self._ctrl_word)
            self.root.after(200, lambda: self._set_connected_ui(True))
        except Exception as e:
            self._set_status(f"清零失败: {e}", "red")

    # ---------------- Worker loop ----------------
    def _worker_loop(self):
        backoff_idx = 0
        while self.running:
            if not self._connected:
                wait_s = RECONNECT_BACKOFF_S[
                    min(backoff_idx, len(RECONNECT_BACKOFF_S) - 1)
                ]
                self.root.after(
                    0,
                    lambda s=wait_s: self._set_status(
                        f"尝试连接 PLC... (退避 {s}s)", "orange"
                    ),
                )
                try:
                    self._open_connection()
                    backoff_idx = 0
                    self.root.after(0, lambda: self._set_connected_ui(True))
                    self.root.after(
                        0,
                        lambda: self.estop_label.config(
                            text="已连接", foreground="green"
                        ),
                    )
                except Exception as e:
                    self._close_connection()
                    self.root.after(
                        0,
                        lambda err=str(e): self._set_status(f"连接失败: {err}", "red"),
                    )
                    backoff_idx += 1
                    time.sleep(wait_s)
                    continue

            try:
                w0, w1, w2 = self._read_words()
                plc_state = w2

                if plc_state == 100:
                    device_status = "急停有效"
                    estop_text = "!!! 急停触发 !!!"
                    estop_color = "red"
                else:
                    status_map = {0: "待机", 20: "运行中"}
                    device_status = status_map.get(plc_state, f"未知 ({plc_state})")
                    estop_text = "正常运行"
                    estop_color = "green"

                self.root.after(
                    0,
                    self._update_labels,
                    w0,
                    w1,
                    w2,
                    device_status,
                    estop_text,
                    estop_color,
                )
            except Exception as e:
                self.root.after(
                    0, lambda err=str(e): self._set_status(f"读取异常: {err}", "red")
                )
                self._close_connection()
                self.root.after(0, lambda: self._set_connected_ui(False))

            time.sleep(POLL_INTERVAL_MS / 1000.0)

    def _update_labels(self, w0, w1, w2, device_status, estop_text, estop_color):
        self.labels["w0"].config(text=f"{w0} (0x{w0:04X})")
        self.labels["w1"].config(text=f"{w1} (0x{w1:04X})")
        self.labels["w2"].config(text=f"{w2} (0x{w2:04X})")
        self.labels["device_status"].config(text=device_status)
        self.estop_label.config(text=estop_text, foreground=estop_color)

    def on_closing(self):
        self.running = False
        try:
            self._close_connection()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PLCMonitorApp(root)
    root.mainloop()
