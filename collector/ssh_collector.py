# collector/ssh_collector.py
import random
import re
import os
import time

class NetworkCollector:
    def __init__(
        self,
        ip,
        user,
        pwd,
        device_type="hp_comware",
        gateway_ip=None,
        use_ai_logic=True,
        thresholds=None,
        ssh_timeout=5,
    ):
        self.ip = ip
        self.user = user
        self.pwd = pwd
        self.device_type = device_type
        self.gateway_ip = gateway_ip or self._default_gateway_ip(ip)
        self.use_ai_logic = bool(use_ai_logic)
        self.thresholds = thresholds or {
            "cpu": 70.0,
            "mem": 80.0,
            "bandwidth_in_util": 80.0,
            "bandwidth_out_util": 80.0,
            "avg_delay_ms": 80.0,
            "packet_loss_pct": 1.0,
        }
        self.ssh_timeout = ssh_timeout

    def _default_gateway_ip(self, ip):
        parts = str(ip).split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            parts[-1] = "1"
            return ".".join(parts)
        return str(ip)

    def _parse_ping(self, output):
        text = str(output)
        loss = 0.0
        loss_match = re.search(r"(\d+(?:\.\d+)?)%\s*packet\s+loss", text, re.IGNORECASE)
        if loss_match:
            loss = float(loss_match.group(1))
        
        avg_delay = 5.0 # 默认内网延迟
        avg_match = re.search(r"rtt\s+min/avg/max/mdev\s+=\s+\d+\.\d+/(\d+\.\d+)/", text, re.IGNORECASE)
        if avg_match:
            avg_delay = float(avg_match.group(1))
        
        return avg_delay, loss

    def _baseline_detect(self, metrics):
        cpu = float(metrics.get("cpu", 0.0) or 0.0)
        mem = float(metrics.get("mem", 0.0) or 0.0)
        in_util = float(metrics.get("bandwidth_in_util", 0.0) or 0.0)
        out_util = float(metrics.get("bandwidth_out_util", 0.0) or 0.0)
        avg_delay = float(metrics.get("avg_delay_ms", 0.0) or 0.0)
        loss = float(metrics.get("packet_loss_pct", 0.0) or 0.0)

        if loss > float(self.thresholds.get("packet_loss_pct", 1.0)):
            return True, "Packet_Loss"
        if avg_delay > float(self.thresholds.get("avg_delay_ms", 80.0)):
            return True, "High_Delay"
        if cpu > float(self.thresholds.get("cpu", 70.0)):
            return True, "High_CPU"
        if mem > float(self.thresholds.get("mem", 80.0)):
            return True, "High_Mem"
        if in_util > float(self.thresholds.get("bandwidth_in_util", 80.0)) or out_util > float(
            self.thresholds.get("bandwidth_out_util", 80.0)
        ):
            return True, "High_Bandwidth"
        return False, "Normal"

    def _collect_via_mininet(self):
        """
        【核心适配】：直接读取 Linux 内核接口统计，替代 SSH 登录
        """
        # 对应 viz_topo.py 中 s1 连接 s2 的接口
        iface = "s1-eth1" 
        path = f"/sys/class/net/{iface}/statistics/"
        
        try:
            # 第一次读取流量
            with open(path + "rx_bytes", "r") as f: rx_start = int(f.read())
            with open(path + "tx_bytes", "r") as f: tx_start = int(f.read())
            
            time.sleep(0.5) # 采样窗口
            
            # 第二次读取流量
            with open(path + "rx_bytes", "r") as f: rx_end = int(f.read())
            with open(path + "tx_bytes", "r") as f: tx_end = int(f.read())

            # 计算带宽利用率 (模拟百兆链路百分比)
            bw_in = round(((rx_end - rx_start) * 8 / (0.5 * 1024 * 1024 * 100)) * 100, 2)
            bw_out = round(((tx_end - tx_start) * 8 / (0.5 * 1024 * 1024 * 100)) * 100, 2)

            # 模拟交换机系统资源占用
            cpu = round(random.uniform(12.0, 28.0), 2)
            mem = round(random.uniform(35.0, 50.0), 2)

            # 对网关执行本地 Ping 探测
            ping_cmd = f"ping -c 3 -W 1 {self.gateway_ip}"
            ping_output = os.popen(ping_cmd).read()
            avg_delay_ms, packet_loss_pct = self._parse_ping(ping_output)

            return {
                "cpu": cpu,
                "mem": mem,
                "delay": round(float(avg_delay_ms), 2),
                "avg_delay_ms": round(float(avg_delay_ms), 2),
                "packet_loss_pct": round(float(packet_loss_pct), 2),
                "bandwidth_in_util": min(bw_in, 100.0),
                "bandwidth_out_util": min(bw_out, 100.0),
                "bandwidth_interfaces": {iface: {"in_util": bw_in, "out_util": bw_out}},
            }
        except Exception as e:
            # 找不到网卡时抛出异常以便进入 mock 模式
            raise Exception(f"Interface {iface} access error: {e}")

    def _collect_mock(self):
        """保留原有的 Mock 逻辑作为兜底"""
        ip_suffix = int(str(self.ip).split(".")[-1]) if "." in str(self.ip) else 0
        final_cpu = round(max(5.0, 15.0 + random.uniform(-3, 5)), 2)
        return {
            "cpu": final_cpu, "mem": 45.0, "delay": 5.0, "avg_delay_ms": 5.0,
            "packet_loss_pct": 0.0, "bandwidth_in_util": 10.0,
            "bandwidth_out_util": 8.0, "bandwidth_interfaces": {},
        }

    def collect(self):
        """
        主采集接口：优先从 Mininet 环境获取真实数据，失败则回退至 Mock
        """
        try:
            metrics = self._collect_via_mininet()
        except Exception:
            metrics = self._collect_mock()

        if metrics and not self.use_ai_logic:
            is_anomaly, fault_type = self._baseline_detect(metrics)
            metrics["is_anomaly"] = int(is_anomaly)
            metrics["fault_type"] = fault_type

        return metrics

    def auto_diagnose(self, fault_type):
        """
        【核心适配】：直接在仿真宿主机执行诊断指令，模拟 AIOps 闭环
        """
        iface = "s1-eth1"
        command_map = {
            "High_CPU": "top -b -n 1 | head -n 10",
            "High_Delay": f"ip -s link show {iface}",
            "High_Bandwidth": f"tc -s qdisc show dev {iface}",
            "Normal": "uptime"
        }
        cmd = command_map.get(fault_type, "uptime")

        try:
            output = os.popen(cmd).read()
            return f"--- Mininet Real-time Diagnosis ---\n{output}"
        except Exception as e:
            return f"MOCK LOG: Diagnosis triggered for {fault_type}. (System busy)"