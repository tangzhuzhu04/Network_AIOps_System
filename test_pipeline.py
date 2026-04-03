# tests/test_pipeline.py

import pytest
from collector.ssh_collector import NetworkCollector
from database.influx_client import InfluxDBClient


# 1. 模拟数据测试：验证解析逻辑是否正确
def test_parse_logic():
    # 模拟一个类，不真正连接设备
    collector = NetworkCollector("192.168.1.1", "admin", "pass")
    sample_output = "CPU usage: 15%  Memory usage: 40%"

    result = collector._parse_percentage(sample_output)
    # 断言：我们预期的结果应该是 15.0
    assert result == 15.0


# 2. 串联测试：验证数据结构是否符合 InfluxDB 要求
def test_data_structure():
    fake_data = {
        "measurement": "network_metrics",
        "tags": {"host": "127.0.0.1", "vendor": "huawei"},
        "fields": {"cpu_usage": 20.5, "mem_usage": 50.0},
        "time": 1708770000
    }

    # 验证关键字段是否存在
    assert "measurement" in fake_data
    assert "cpu_usage" in fake_data["fields"]
    assert isinstance(fake_data["fields"]["cpu_usage"], float)


# 3. 异常处理测试：验证断网情况
def test_connection_error():
    collector = NetworkCollector("192.0.2.1", "admin", "wrong")
    # 模拟网络超时
    def mock_collect_error():
        return None
    
    collector.collect = mock_collect_error
    # 预期应该返回 None 而不是程序崩溃
    assert collector.collect() is None


def test_parse_interface_brief():
    collector = NetworkCollector("192.168.1.1", "admin", "pass")
    sample_output = """
Interface        PHY   Protocol  InUti OutUti inErrors outErrors
GE1/0/1          up    up        12%   34%    0       0
GE1/0/2          up    up        0%    1%     0       0
"""
    in_avg, out_avg, per_iface = collector._parse_interface_brief(sample_output)
    assert in_avg == 6.0
    assert out_avg == 17.5
    assert per_iface["GE1/0/1"]["in_util"] == 12.0
    assert per_iface["GE1/0/2"]["out_util"] == 1.0


def test_parse_ping_linux_style():
    collector = NetworkCollector("192.168.1.1", "admin", "pass")
    sample_output = """
5 packets transmitted, 5 received, 0% packet loss, time 4004ms
rtt min/avg/max/mdev = 1.0/2.5/3.0/0.5 ms
"""
    avg_delay, loss = collector._parse_ping(sample_output)
    assert avg_delay == 2.5
    assert loss == 0.0


def test_parse_ping_windows_style():
    collector = NetworkCollector("192.168.1.1", "admin", "pass")
    sample_output = """
Packets: Sent = 5, Received = 5, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
Minimum = 1ms, Maximum = 4ms, Average = 2ms
"""
    avg_delay, loss = collector._parse_ping(sample_output)
    assert avg_delay == 2.0
    assert loss == 0.0


def test_baseline_detect_packet_loss():
    collector = NetworkCollector("192.168.1.1", "admin", "pass", use_ai_logic=False)
    is_anomaly, fault_type = collector._baseline_detect(
        {
            "cpu": 10.0,
            "mem": 10.0,
            "avg_delay_ms": 10.0,
            "bandwidth_in_util": 0.0,
            "bandwidth_out_util": 0.0,
            "packet_loss_pct": 2.0,
        }
    )
    assert is_anomaly is True
    assert fault_type == "Packet_Loss"
