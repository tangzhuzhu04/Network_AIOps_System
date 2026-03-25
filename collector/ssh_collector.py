# collector/ssh_collector.py

import re
from netmiko import ConnectHandler


class NetworkDeviceCollector:
    """
    这是一个【类】：专门负责与网络设备打交道
    """

    def __init__(self, device_info):
        """
        构造方法：初始化设备的 IP、账号、密码等信息
        """
        self.device_info = device_info
        # 根据开题报告，定义不同厂商的命令映射
        self.commands = {
            'huawei': 'display cpu-usage',
            'hp_comware': 'display cpu'
        }

    def get_cpu_data(self):
        """
        这是一个【方法】：具体执行“获取CPU数据”的动作
        """
        try:
            # 建立连接
            with ConnectHandler(**self.device_info) as ssh:
                vendor = self.device_info['device_type']
                cmd = self.commands.get(vendor)
                output = ssh.send_command(cmd)

                # 调用解析逻辑（下面定义的私有方法）
                return self._parse_percentage(output)
        except Exception as e:
            print(f"连接失败: {e}")
            return None

    def _parse_percentage(self, text):
        """
        【私有方法】：用正则表达式从回显文字中提取数字
        """
        match = re.search(r"(\d+)%", text)
        return float(match.group(1)) if match else 0.0