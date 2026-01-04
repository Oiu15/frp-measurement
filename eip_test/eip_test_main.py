import time
import numpy as np
from pycomm3 import CIPDriver


def main():
    plc_ip = "192.168.6.6"  # 你的信捷PLC IP

    with CIPDriver(plc_ip) as plc:
        if not plc.connected:
            print("连接失败！检查IP、网络、PLC运行状态。")
            return

        print("Explicit连接成功！开始轮询读取D1000开始的100字数据。")

        while True:
            try:
                # 读Assembly Object实例100（T→O），属性3 = 数据（标准CIP Assembly读法）
                response = plc.generic_message(
                    service=0x0E,  # Get_Attribute_Single
                    class_code=0x04,  # Assembly Object
                    instance=100,  # 你的T→O实例ID=100
                    attribute=3,  # 数据属性
                    data_type=None,  # 自动推断（返回bytes）
                    name="read_assembly",
                )

                if response:
                    data_bytes = response.value  # 返回bytes，总200字节（100字）
                    arr = np.frombuffer(data_bytes, dtype=np.int16)  # 信捷数据通常INT16
                    print(f"收到 {len(arr)} 个字，前10个: {arr[:10]}")
                    # 这里放你的拟合逻辑
                    # angles = arr[:50] ...
                    # measurements = arr[50:] ...
                else:
                    print(f"读取错误: {response.error}")

            except Exception as e:
                print(f"异常: {e}")

            time.sleep(0.02)  # 20ms轮询（可调5-50ms，根据实时需求）


if __name__ == "__main__":
    main()
