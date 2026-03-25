# main.py
import time
import numpy as np
from collector.ssh_collector import NetworkDeviceCollector
from collector.preprocess import DataPreprocessor
from database.influx_client import InfluxDBManager
from models.anomaly_detector import AnomalyDetector

# 如果你写了诊断模型，也一并引入
# from models.diagnosis_model import DiagnosisModel

# 1. 初始化配置与实例
DEVICE_CONFIG = {
    'device_type': 'huawei',
    'host': '192.168.1.1',
    'username': 'admin',
    'password': 'password123'
}

# 按照开题报告，使用 InfluxDB 存储指标
db = InfluxDBManager(token="YOUR_TOKEN", org="YOUR_ORG", bucket="network_data")
collector = NetworkDeviceCollector(DEVICE_CONFIG)
preprocessor = DataPreprocessor(window_size=5)
detector = AnomalyDetector(contamination=0.1)


def run_system():
    print("--- 智能网络运维系统启动 ---")

    # 模拟：实际项目中这里应先从数据库加载历史数据进行模型训练
    # detector.train(historical_data)

    while True:
        try:
            # 步骤 A: 数据采集
            cpu_val = collector.get_cpu_data()
            if cpu_val is None:
                time.sleep(10)
                continue

            # 步骤 B: 构造原始数据并进行预处理
            # 实际开发中，预处理通常需要一个滑动窗口的列表数据
            raw_metrics = {"cpu_usage": cpu_val, "mem_usage": 40.0}  # 示例

            # 步骤 C: 异常检测 (AI大脑预警)
            # 将当前特征转为模型需要的 numpy 格式
            current_feature = np.array([cpu_val, 40.0, cpu_val])  # 示例特征向量
            is_anomaly = detector.predict(current_feature)

            # 步骤 D: 结果处理与自动诊断
            status = "正常"
            if is_anomaly == 1:
                status = "异常告警"
                print(f"【！数据预警】检测到网络指标异常，当前值: {cpu_val}%")
                # 此处可调用自动诊断模块：diagnosis = diagnoser.diagnose(current_feature)
            else:
                print(f"【监控中】网络运行正常，当前值: {cpu_val}%")

            # 步骤 E: 数据入库 (供前端可视化展示)
            data_to_db = {
                "measurement": "network_status",
                "tags": {"host": DEVICE_CONFIG['host'], "status": status},
                "fields": {"cpu_usage": float(cpu_val)},
                "time": int(time.time())
            }
            db.save_metrics(data_to_db)

            # 按照开题报告设定的频率采集（如按分钟级）
            time.sleep(60)

        except KeyboardInterrupt:
            print("系统安全退出")
            break


if __name__ == "__main__":
    run_system()