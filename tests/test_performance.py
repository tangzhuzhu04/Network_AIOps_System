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


def test_anomaly_detection_latency(trained_detector, benchmark=None):
    """
    性能测试：测量模型单次预测的耗时
    """
    # 1. 准备模拟输入数据 (1条包含3个维度的特征)
    mock_feature = np.random.rand(1, 3)

    # 如果没有安装 pytest-benchmark，则使用普通测试
    if benchmark:
        result = benchmark(trained_detector.predict, mock_feature)
    else:
        import time
        start = time.time()
        result = trained_detector.predict(mock_feature)
        end = time.time()
        print(f"预测耗时: {end-start:.6f}s")

    # 3. 断言确保有输出 (predict 返回 int)
    assert result in [0, 1]

# 运行命令：
# pytest tests/test_performance.py --benchmark-autosave --html=report.html