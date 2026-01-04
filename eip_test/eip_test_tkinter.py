import tkinter as tk
from tkinter import ttk
import time
import numpy as np
from pycomm3 import CIPDriver
import threading

# ==================== 配置区 ====================
PLC_IP = "192.168.6.6"  # 你的信捷PLC IP
INSTANCE_ID = 100  # T→O 实例ID（与PLC配置一致）
WORD_COUNT = 3  # 读取 3 个字：HD1000, HD1001, HD1002
POLL_INTERVAL_MS = 500  # 刷新间隔 500ms（可改为 200 更快）
# ===============================================


class PLCMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("信捷PLC 状态监控（EIP）")
        self.root.geometry("520x360")
        self.root.configure(bg="#f0f0f0")

        # 标题
        tk.Label(
            root,
            text="信捷PLC 实时状态监控",
            font=("Microsoft YaHei", 18, "bold"),
            bg="#f0f0f0",
        ).pack(pady=15)

        # 数据显示框架
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        self.labels = {}

        # 定义显示项目
        items = [
            ("周期计数 (HD1000)", "cycle_cnt"),
            ("1Hz 心跳 (HD1001)", "heartbeat"),
            ("状态字 (HD1002)", "state_word"),
            ("当前设备状态", "device_status"),  # 根据状态字解释
        ]

        for text, key in items:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=10)

            ttk.Label(
                row, text=text + "：", width=18, font=("Microsoft YaHei", 11)
            ).pack(side=tk.LEFT)
            val_label = ttk.Label(
                row, text="---", font=("Consolas", 14), foreground="blue"
            )
            val_label.pack(side=tk.LEFT)
            self.labels[key] = val_label

        # 急停大提示（单独一行，醒目）
        self.estop_frame = ttk.Frame(frame)
        self.estop_frame.pack(fill=tk.X, pady=15)
        self.estop_label = ttk.Label(
            self.estop_frame,
            text="正常运行",
            font=("Microsoft YaHei", 16, "bold"),
            foreground="green",
            background="#f0f0f0",
        )
        self.estop_label.pack()

        # 连接状态
        self.status_label = ttk.Label(
            root,
            text="连接状态：未连接",
            foreground="red",
            font=("Microsoft YaHei", 10),
        )
        self.status_label.pack(pady=10)

        # 启动后台线程
        self.running = True
        self.plc = None
        threading.Thread(target=self.connect_and_poll, daemon=True).start()

        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def connect_and_poll(self):
        try:
            self.plc = CIPDriver(PLC_IP)
            self.plc.__enter__()
            self.root.after(
                0,
                lambda: self.status_label.config(
                    text="连接状态：已连接", foreground="green"
                ),
            )

            while self.running:
                try:
                    response = self.plc.generic_message(
                        service=0x0E,
                        class_code=0x04,
                        instance=INSTANCE_ID,
                        attribute=3,
                        data_type=None,
                    )

                    if response and response.value:
                        data_bytes = response.value
                        arr = np.frombuffer(data_bytes, dtype=np.int16)

                        if len(arr) >= WORD_COUNT:
                            cycle_cnt = int(arr[0])
                            heartbeat = int(arr[1])
                            state_word = int(arr[2]) & 0xFFFF

                            # 根据状态字判断设备状态
                            if state_word == 100:
                                device_status = "急停有效"
                                estop_text = "!!! 急停触发 !!!"
                                estop_color = "red"
                            else:
                                # 可扩展其他状态
                                status_map = {
                                    0: "待机",
                                    10: "就绪",
                                    20: "运行中",
                                    30: "测量中",
                                    50: "暂停",
                                }
                                device_status = status_map.get(
                                    state_word, f"未知状态 ({state_word})"
                                )
                                estop_text = "正常运行"
                                estop_color = "green"

                            # 更新界面
                            self.root.after(
                                0,
                                self.update_labels,
                                cycle_cnt,
                                heartbeat,
                                state_word,
                                device_status,
                                estop_text,
                                estop_color,
                            )
                    else:
                        self.root.after(
                            0,
                            lambda: self.status_label.config(
                                text="读取失败", foreground="orange"
                            ),
                        )

                except Exception as e:
                    self.root.after(
                        0,
                        lambda: self.status_label.config(
                            text=f"读取异常: {e}", foreground="red"
                        ),
                    )

                time.sleep(POLL_INTERVAL_MS / 1000.0)

        except Exception as e:
            self.root.after(
                0,
                lambda: self.status_label.config(
                    text=f"连接失败: {e}", foreground="red"
                ),
            )

    def update_labels(
        self, cycle_cnt, heartbeat, state_word, device_status, estop_text, estop_color
    ):
        self.labels["cycle_cnt"].config(text=str(cycle_cnt))
        self.labels["heartbeat"].config(text=str(heartbeat))
        self.labels["state_word"].config(text=f"{state_word} (0x{state_word:04X})")
        self.labels["device_status"].config(text=device_status)

        # 急停大字提示
        self.estop_label.config(text=estop_text, foreground=estop_color)

    def on_closing(self):
        self.running = False
        if self.plc:
            try:
                self.plc.__exit__(None, None, None)
            except:
                pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PLCMonitorApp(root)
    root.mainloop()
