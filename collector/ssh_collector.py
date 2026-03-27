# collector/ssh_collector.py
import time
import random
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException


class NetworkCollector:
    def __init__(self, ip, user, pwd):
        self.ip = ip
        self.user = user
        self.pwd = pwd

    def _parse_percentage(self, output):
        """解析 SSH 输出中的百分比数值"""
        import re
        match = re.search(r"(\d+(\.\d+)?)%", output)
        if match:
            return float(match.group(1))
        return 0.0

    def collect(self):
        """
        模拟采集逻辑或通过 SSH 获取实时数据
        【虚拟化适配】：根据不同 IP 生成差异化的动态随机数据
        """
        try:
            # 根据 IP 尾数设置不同的“性格”
            ip_suffix = int(self.ip.split('.')[-1])
            
            # 基础值
            base_cpu = 15.0 + (ip_suffix % 5) * 5  # 不同设备基础 CPU 不同
            base_mem = 40.0 + (ip_suffix % 3) * 10 # 不同设备基础 内存 不同
            base_delay = 10.0 + (ip_suffix % 4) * 5 # 不同设备基础 延迟 不同

            # 随机波动
            cpu_fluctuation = random.uniform(-3.0, 5.0)
            mem_fluctuation = random.uniform(-5.0, 5.0)
            delay_fluctuation = random.uniform(-2.0, 2.0)

            # 模拟不同场景的异常
            anomaly_chance = 0.1
            if ip_suffix == 1: # 核心交换机：偶尔 CPU 飙升
                if random.random() < 0.15:
                    cpu_fluctuation += random.uniform(50.0, 70.0)
            elif ip_suffix == 2: # 接入交换机：偶尔 延迟 变大
                if random.random() < 0.2:
                    delay_fluctuation += random.uniform(100.0, 200.0)
            elif ip_suffix == 3: # 家用路由器：偶尔 内存 泄漏
                if random.random() < 0.1:
                    mem_fluctuation += random.uniform(30.0, 50.0)

            final_cpu = round(max(5, base_cpu + cpu_fluctuation), 2)
            final_mem = round(max(10, base_mem + mem_fluctuation), 2)
            final_delay = round(max(1, base_delay + delay_fluctuation), 2)

            return {
                'cpu': final_cpu,
                'mem': final_mem,
                'delay': final_delay
            }
        except Exception as e:
            print(f"Collect error: {e}")
            return None

    def auto_diagnose(self, fault_type):
        """
        对应开题报告：自动验证模块 (Netmiko执行诊断命令)
        当异常发生时，根据故障类型下发诊断指令
        """
        device = {
            'device_type': 'hp_comware',  # 需根据你的设备（如H3C/华为）调整
            'host': self.ip,
            'username': self.user,
            'password': self.pwd,
        }

        # 针对不同预测结果的诊断指令集
        command_map = {
            "High_CPU": "display cpu-usage",
            "High_Delay": "display interface brief",
            "Normal": "display logbuffer"
        }
        cmd = command_map.get(fault_type, "display clock")

        try:
            # 建立 SSH 连接并抓取现场
            # 注意：在没有实体设备的情况下，这里会由于连接超时进入 except 分支
            with ConnectHandler(**device) as net_connect:
                output = net_connect.send_command(cmd)
                return output
        except Exception as e:
            # 【虚拟化适配】：如果没有实体设备，返回模拟的诊断结果以演示 AIOps 闭环
            mock_logs = {
                "High_CPU": f"MOCK LOG: Process 'SNMP' is consuming 85% CPU on {self.ip}",
                "High_Delay": f"MOCK LOG: Interface GigabitEthernet0/1 has high input errors on {self.ip}",
                "Normal": "MOCK LOG: System status is healthy, check logbuffer for minor events."
            }
            return mock_logs.get(fault_type, f"MOCK LOG: Automatic diagnosis triggered for {fault_type}. (Device offline)")