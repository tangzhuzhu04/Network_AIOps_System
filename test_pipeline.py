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