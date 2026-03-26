# tests/test_performance.py
import pytest
import numpy as np
from models.anomaly_detector import AnomalyDetector


@pytest.fixture
def trained_detector():
    """初始化并预热模型"""
    detector = AnomalyDetector()
    dummy_data = np.random.rand(500, 3)
    detector.train(dummy_data)
    return detector


def test_anomaly_detection_latency(benchmark, trained_detector):
    """
    性能测试：测量模型单次预测的耗时
    """
    # 1. 准备模拟输入数据 (1条包含3个维度的特征)
    mock_feature = np.random.rand(1, 3)

    # 2. 正确调用 benchmark：第一个参数是函数名，后面是传给该函数的参数
    # 系统会自动多次运行 predict(mock_feature) 并统计平均时间
    result = benchmark(trained_detector.predict, mock_feature)

    # 3. 断言确保有输出
    assert len(result) == 1

# 运行命令：
# pytest tests/test_performance.py --benchmark-autosave --html=report.html