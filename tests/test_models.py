# tests/test_models.py
import pytest
import numpy as np
from models.anomaly_detector import AnomalyDetector
from models.diagnosis_model import DiagnosisModel


@pytest.fixture
def model_suite():
    """初始化模型组件供测试使用"""
    detector = AnomalyDetector()
    diagnoser = DiagnosisModel()
    return detector, diagnoser


def test_anomaly_detection(model_suite):
    """测试孤立森林是否能识别明显的异常"""
    detector, _ = model_suite
    # 模拟正常的低负载数据进行简单训练（实际应加载训练好的模型）
    normal_train = np.random.normal(20, 2, (50, 3))
    detector.train(normal_train)

    # 输入一个极高的 CPU 数值 (99%)
    high_cpu_data = np.array([99.0, 40.0, 80.0])
    assert detector.predict(high_cpu_data) == 1  # 预期应识别为异常


def test_diagnosis_accuracy(model_suite):
    """测试随机森林是否能正确区分故障根因"""
    _, diagnoser = model_suite
    # 构造模拟标签数据：0-正常, 1-带宽拥堵, 2-端口故障
    X_train = np.array([[20, 30, 10], [90, 40, 80], [25, 35, 0]])
    y_train = np.array([0, 1, 2])
    diagnoser.train(X_train, y_train)

    # 模拟一个流量巨大的场景，看它是否诊断为“带宽拥堵”
    congestion_data = np.array([85.0, 45.0, 75.0])
    result = diagnoser.diagnose(congestion_data)
    assert result == "带宽拥堵"  # 预期诊断结果