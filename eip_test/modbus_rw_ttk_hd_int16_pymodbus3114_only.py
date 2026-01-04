"""
modbus_rw_ttk_hd.py

Tkinter + pymodbus Modbus-TCP client for XINJE PLC (or any Modbus-TCP server).

Verified mapping in your test:
- Write control word to D100 (Holding Register address 100):
    value 1  -> bit0 = 1 (START)
    value 2  -> bit1 = 1 (STOP)
  (pulse then clear back to 0)

- Read status from HD1000~HD1002 (INT16) at Holding Register start address 42088:
    total 3 x 16-bit registers (3 x INT16)

Notes:
- WORD_ORDER_UNUSED matters for 32-bit decoding. Your test tool showed that
  regs[0]=0x1089, regs[1]=0xF82F decoded to -131133303, which corresponds to
  LOW word first (LH). Therefore default WORD_ORDER_UNUSED = "lh".
"""

import threading
import time
import tkinter as tk
from tkinter import ttk

from pymodbus.client import ModbusTcpClient

def mb_read_holding_registers(client: ModbusTcpClient, address: int, count: int, device_id: int):
    """
    pymodbus 3.11.x API: use device_id= (Modbus TCP Unit Identifier).
    """
    return client.read_holding_registers(address=address, count=count, device_id=device_id)


def mb_write_register(client: ModbusTcpClient, address: int, value: int, device_id: int):
    """
    pymodbus 3.11.x API: use device_id= (Modbus TCP Unit Identifier).
    """
    return client.write_register(address=address, value=value, device_id=device_id)  # FC06


# ==================== 配置区（按你实测） ====================
PLC_IP = "192.168.6.6"
PLC_PORT = 502
UNIT_ID = 1  # 有些PLC忽略；保留即可

# 写：D100（控制字）
WRITE_ADDR = 100            # D100
WRITE_PULSE_MS = 200        # 脉冲保持时间(ms)，之后自动写0清除
CLEAR_AFTER_PULSE = True

# 读：HD1000~HD1002（每个为 INT16，占1个寄存器）
READ_ADDR = 42088           # 你调试工具中验证成功的起始地址（对应HD1000）
READ_COUNT = 3              # 3个HD * 1个寄存器
# WORD_ORDER_UNUSED 对 INT16 无意义；若后续改为32/64位再考虑字序

POLL_INTERVAL_MS = 200      # UI轮询周期
RECONNECT_BACKOFF_S = (1, 2, 5)
# ============================================================


def u16(x: int) -> int:
    return x & 0xFFFF


def s16(x: int) -> int:
    """Convert a 16-bit value to signed INT16."""
    x = u16(x)
    if x & 0x8000:
        x -= 0x10000
    return x



class ModbusHDApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Modbus TCP - D100控制字 & HD1000~1002状态监视")
        self.root.geometry("760x420")

        self._client_lock = threading.Lock()
        self._client: ModbusTcpClient | None = None
        self._connected = False
        self._running = True

        # ---------- UI ----------
        top = ttk.Frame(root, padding=12)
        top.pack(fill=tk.X)

        ttk.Label(top, text="PLC IP:").pack(side=tk.LEFT)
        self.ip_var = tk.StringVar(value=PLC_IP)
        ttk.Entry(top, textvariable=self.ip_var, width=16).pack(side=tk.LEFT, padx=(6, 12))

        ttk.Label(top, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.IntVar(value=PLC_PORT)
        ttk.Entry(top, textvariable=self.port_var, width=6).pack(side=tk.LEFT, padx=(6, 12))

        self.btn_connect = ttk.Button(top, text="连接", command=self.manual_connect)
        self.btn_connect.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="未连接")
        ttk.Label(top, textvariable=self.status_var, foreground="blue").pack(side=tk.LEFT, padx=12)

        # Display frame
        disp = ttk.LabelFrame(root, text="实时数据（HD1000~1002）", padding=12)
        disp.pack(fill=tk.X, padx=12, pady=8)

        self.lbl_hd = {}
        for name in ["HD1000", "HD1001", "HD1002"]:
            row = ttk.Frame(disp)
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=f"{name} (int16):", width=18).pack(side=tk.LEFT)
            v = ttk.Label(row, text="---", font=("Consolas", 14))
            v.pack(side=tk.LEFT)
            self.lbl_hd[name] = v

        rawf = ttk.LabelFrame(root, text="原始寄存器（3×16bit）", padding=12)
        rawf.pack(fill=tk.X, padx=12, pady=8)

        self.raw_var = tk.StringVar(value="---")
        ttk.Label(rawf, textvariable=self.raw_var, font=("Consolas", 12)).pack(anchor="w")

        # Control frame
        ctl = ttk.LabelFrame(root, text="控制（写 D100 控制字）", padding=12)
        ctl.pack(fill=tk.X, padx=12, pady=8)

        self.btn_start = ttk.Button(ctl, text="启动 (bit0)", command=lambda: self.send_mask(0))
        self.btn_start.pack(side=tk.LEFT, padx=6)

        self.btn_stop = ttk.Button(ctl, text="停止 (bit1)", command=lambda: self.send_mask(1))
        self.btn_stop.pack(side=tk.LEFT, padx=6)

        ttk.Label(ctl, text="脉冲(ms):").pack(side=tk.LEFT, padx=(18, 6))
        self.pulse_var = tk.IntVar(value=WRITE_PULSE_MS)
        ttk.Entry(ctl, textvariable=self.pulse_var, width=6).pack(side=tk.LEFT)

        self.btn_zero = ttk.Button(ctl, text="手动清零(写0)", command=lambda: self.write_word(0))
        self.btn_zero.pack(side=tk.LEFT, padx=18)

        # start worker
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- Connection ----------
    def manual_connect(self):
        # Force reconnect now
        self._close()
        self._set_status("尝试连接...", "orange")

    def _connect(self) -> bool:
        ip = self.ip_var.get().strip()
        port = int(self.port_var.get())
        cli = ModbusTcpClient(host=ip, port=port, timeout=1.0)
        if not cli.connect():
            try:
                cli.close()
            except Exception:
                pass
            return False
        with self._client_lock:
            self._client = cli
        return True

    def _close(self):
        with self._client_lock:
            cli = self._client
            self._client = None
        if cli is not None:
            try:
                cli.close()
            except Exception:
                pass
        self._connected = False

    def _set_status(self, msg: str, color: str = "blue"):
        self.status_var.set(msg)

    # ---------- Modbus ops ----------
    def _read_regs(self) -> list[int]:
        with self._client_lock:
            cli = self._client
        if cli is None:
            raise RuntimeError("not connected")

        # Use compatibility wrapper (pymodbus 3.11.4 expects device_id=)
        rr = mb_read_holding_registers(cli, address=READ_ADDR, count=READ_COUNT, unit_id=UNIT_ID)
        if rr.isError():
            raise RuntimeError(f"Modbus read error: {rr}")
        regs = list(rr.registers)
        if len(regs) != READ_COUNT:
            raise RuntimeError(f"read count mismatch: expected {READ_COUNT}, got {len(regs)}")
        return regs

    def write_word(self, value_u16: int):
        value_u16 = int(value_u16) & 0xFFFF
        with self._client_lock:
            cli = self._client
        if cli is None:
            self._set_status("未连接，无法写入", "red")
            return
        # Use compatibility wrapper (pymodbus 3.11.4 expects device_id=)
        wr = mb_write_register(cli, address=WRITE_ADDR, value=value_u16, unit_id=UNIT_ID)  # FC06
        if wr.isError():
            self._set_status(f"写入失败: {wr}", "red")
        else:
            self._set_status(f"已写 D100={value_u16} (0x{value_u16:04X})", "green")

    def send_mask(self, bit_index: int):
        """
        Write exactly one-bit mask to D100:
          bit0 -> 1
          bit1 -> 2
        then (optionally) clear to 0 after pulse.
        """
        if bit_index < 0 or bit_index > 15:
            self._set_status("bit 超范围(0..15)", "red")
            return
        mask = 1 << bit_index

        self.write_word(mask)

        if CLEAR_AFTER_PULSE:
            pulse_ms = max(0, int(self.pulse_var.get()))
            if pulse_ms > 0:
                self.root.after(pulse_ms, lambda: self.write_word(0))

    # ---------- Worker loop ----------
    def _worker_loop(self):
        backoff_idx = 0
        while self._running:
            if not self._connected:
                wait_s = RECONNECT_BACKOFF_S[min(backoff_idx, len(RECONNECT_BACKOFF_S) - 1)]
                try:
                    ok = self._connect()
                    if ok:
                        self._connected = True
                        backoff_idx = 0
                        self.root.after(0, lambda: self._set_status("已连接", "green"))
                    else:
                        backoff_idx += 1
                        self.root.after(0, lambda s=wait_s: self._set_status(f"连接失败，{s}s后重试", "red"))
                        time.sleep(wait_s)
                        continue
                except Exception as e:
                    backoff_idx += 1
                    self.root.after(0, lambda err=str(e), s=wait_s: self._set_status(f"连接异常: {err}，{s}s后重试", "red"))
                    time.sleep(wait_s)
                    continue

            # connected: poll
            try:
                regs = self._read_regs()
                # decode three INT16 (HD1000~HD1002)
                v0 = s16(regs[0])
                v1 = s16(regs[1])
                v2 = s16(regs[2])

                raw_txt = " ".join([f"R{i}={r:5d}(0x{r:04X})" for i, r in enumerate(regs)])
                self.root.after(0, self._update_ui, v0, v1, v2, raw_txt)
            except Exception as e:
                # drop connection and retry
                self.root.after(0, lambda err=str(e): self._set_status(f"读取异常: {err}", "red"))
                self._close()

            time.sleep(POLL_INTERVAL_MS / 1000.0)

    def _update_ui(self, v0: int, v1: int, v2: int, raw_txt: str):
        self.lbl_hd["HD1000"].config(text=f"{v0}")
        self.lbl_hd["HD1001"].config(text=f"{v1}")
        self.lbl_hd["HD1002"].config(text=f"{v2}")
        self.raw_var.set(raw_txt)

    def on_close(self):
        self._running = False
        try:
            self._close()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusHDApp(root)
    root.mainloop()