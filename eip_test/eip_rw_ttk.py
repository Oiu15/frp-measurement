"""
eip_rw_ttk.py (revised)
- Keep using pycomm3.CIPDriver + explicit Assembly read/write (Class 0x04, Attr 3)
- Robust reconnect with backoff (1s, 2s, 5s loop)
- Removes numpy dependency; uses struct for correct endian/word handling
- Treats T->O(100) as 3 * UINT16 words (6 bytes), O->T(101) as 1 * UINT16 (2 bytes)
- Adds "pulse" behavior for Start/Stop buttons (optional, default ON)
"""

import tkinter as tk
from tkinter import ttk
import time
import struct
import threading
from pycomm3 import CIPDriver

# ==================== 配置区 ====================
PLC_IP = "192.168.6.6"

# Assembly Instances
T_O_INSTANCE = 100  # 读：T->O (PLC->PC) 3 words => 6 bytes
O_T_INSTANCE = 101  # 写：O->T (PC->PLC) 1 word  => 2 bytes

POLL_INTERVAL_MS = 200  # 读周期：UI显示一般 100~300ms 足够
WRITE_PULSE_MS = 200  # 按钮脉冲宽度；设为 0 表示不脉冲（保持位）
ENABLE_WRITE_PULSE = True  # True: 写1再自动清0；False: 只写一次（保持）

# 重连退避：循环使用 1s/2s/5s
RECONNECT_BACKOFF_S = (1, 2, 5)
# ===============================================


class PLCMonitorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("信捷PLC 监控与控制（EIP 显式 Assembly 读写）")
        self.root.geometry("580x480")
        self.root.configure(bg="#f0f0f0")

        tk.Label(
            root,
            text="信捷PLC 控制面板",
            font=("Microsoft YaHei", 18, "bold"),
            bg="#f0f0f0",
        ).pack(pady=15)

        # 数据显示区
        frame_display = ttk.LabelFrame(root, text="实时状态", padding=15)
        frame_display.pack(fill=tk.X, padx=20, pady=10)

        self.labels = {}
        items = [
            (f"Word0 (T→O inst {T_O_INSTANCE})", "w0"),
            (f"Word1 (T→O inst {T_O_INSTANCE})", "w1"),
            (f"Word2/STATE (T→O inst {T_O_INSTANCE})", "w2"),
            ("当前设备状态", "device_status"),
        ]
        for text, key in items:
            row = ttk.Frame(frame_display)
            row.pack(fill=tk.X, pady=6)
            ttk.Label(
                row, text=text + "：", width=28, font=("Microsoft YaHei", 11)
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

        # 控制按钮区
        frame_control = ttk.LabelFrame(
            root, text="虚拟操作按钮（写 O→T 控制字）", padding=20
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

        # 连接状态
        self.status_label = ttk.Label(root, text="连接状态：未连接", foreground="red")
        self.status_label.pack(pady=10)

        # runtime state
        self.running = True
        self._plc = None
        self._plc_lock = threading.Lock()
        self._connected = False

        # 控制字缓存（避免多个按钮同时写时互相覆盖）
        self._ctrl_word = 0

        threading.Thread(target=self._worker_loop, daemon=True).start()
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ---------------- PLC low-level helpers ----------------
    def _set_status(self, text: str, color: str = "black"):
        self.status_label.config(text=text, foreground=color)

    def _set_connected_ui(self, ok: bool):
        if ok:
            self._set_status("连接状态：已连接", "green")
        else:
            self._set_status("连接状态：未连接", "red")

    def _open_connection(self):
        """(Re)open CIPDriver connection; caller in worker thread."""
        with self._plc_lock:
            # close old if any
            try:
                if self._plc is not None:
                    self._plc.__exit__(None, None, None)
            except Exception:
                pass
            self._plc = None

            plc = CIPDriver(PLC_IP)
            plc.__enter__()
            self._plc = plc
            self._connected = True

    def _close_connection(self):
        with self._plc_lock:
            try:
                if self._plc is not None:
                    self._plc.__exit__(None, None, None)
            except Exception:
                pass
            self._plc = None
            self._connected = False

    def _read_t_o_words(self):
        """Read T->O assembly (instance 100) attr 3; return tuple(w0,w1,w2) as UINT16."""
        with self._plc_lock:
            plc = self._plc
        if plc is None:
            raise RuntimeError("PLC not connected")

        resp = plc.generic_message(
            service=0x0E,  # Get_Attribute_Single
            class_code=0x04,  # Assembly Object
            instance=T_O_INSTANCE,
            attribute=3,
            data_type=None,
        )

        raw = getattr(resp, "value", None)
        if not raw or len(raw) < 6:
            raise RuntimeError(
                f"T→O 数据长度不足: got={0 if not raw else len(raw)} bytes, need>=6"
            )

        # 3 * uint16 little-endian
        w0, w1, w2 = struct.unpack_from("<HHH", raw, 0)
        return w0, w1, w2

    def _write_o_t_word(self, word_u16: int):
        """Write O->T assembly (instance 101) attr 3; word_u16 is UINT16."""
        if not (0 <= word_u16 <= 0xFFFF):
            raise ValueError("word_u16 must be 0..65535")

        with self._plc_lock:
            plc = self._plc
        if plc is None:
            raise RuntimeError("PLC not connected")

        plc.generic_message(
            service=0x10,  # Set_Attribute_Single
            class_code=0x04,  # Assembly Object
            instance=O_T_INSTANCE,
            attribute=3,
            data=struct.pack("<H", word_u16),
            data_type=None,
        )

    # ---------------- UI actions ----------------
    def send_command_bit(self, bit_index: int):
        """
        UI thread: set a bit in ctrl_word and write to PLC.
        If ENABLE_WRITE_PULSE: auto-clear after WRITE_PULSE_MS.
        """
        if bit_index < 0 or bit_index > 15:
            self._set_status("命令位超范围(0..15)", "red")
            return

        if not self._connected:
            self._set_status("连接失败，无法发送命令", "red")
            return

        mask = 1 << bit_index

        # Update cached ctrl_word
        self._ctrl_word |= mask

        # Try write immediately
        try:
            self._write_o_t_word(self._ctrl_word)
            self._set_status(
                f"已发送命令：Bit{bit_index}=1 (ctrl=0x{self._ctrl_word:04X})", "blue"
            )
        except Exception as e:
            self._set_status(f"发送失败: {e}", "red")
            return

        if ENABLE_WRITE_PULSE and WRITE_PULSE_MS > 0:
            # schedule clear
            self.root.after(WRITE_PULSE_MS, lambda: self._clear_command_bit(bit_index))

    def _clear_command_bit(self, bit_index: int):
        """UI thread: clear bit and write back (pulse end)."""
        if not self._connected:
            return
        mask = 1 << bit_index
        self._ctrl_word &= (~mask) & 0xFFFF
        try:
            self._write_o_t_word(self._ctrl_word)
            # Do not spam UI; just restore connected status after a short moment
            self.root.after(200, lambda: self._set_connected_ui(True))
        except Exception as e:
            self._set_status(f"清零失败: {e}", "red")

    # ---------------- Worker loop ----------------
    def _worker_loop(self):
        backoff_idx = 0
        while self.running:
            if not self._connected:
                # attempt connect with backoff
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

            # connected -> poll
            try:
                w0, w1, w2 = self._read_t_o_words()

                # 你原逻辑把第三个 word 当 PLC_STATE；这里沿用
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
                # read failed -> mark disconnected and retry
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
