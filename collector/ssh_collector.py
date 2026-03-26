# collector/ssh_collector.py
import time
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException


class NetworkCollector:
    def __init__(self, ip, user, pwd):
        self.ip = ip
        self.user = user
        self.pwd = pwd

    def collect(self):
        """
        模拟采集逻辑或通过 SSH 获取实时数据
        """
        try:
            # 实际项目中这里应通过 netmiko 发送采集指令
            # 此处返回模拟数据用于测试闭环
            return {
                'cpu': 15.5,
                'mem': 45.2,
                'delay': 12.0
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
            with ConnectHandler(**device) as net_connect:
                output = net_connect.send_command(cmd)
                return output
        except Exception as e:
            return f"Auto-diagnosis failed: {str(e)}"