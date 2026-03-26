# main.py
import time
import logging
import numpy as np
from collector.ssh_collector import NetworkCollector
from database.influx_client import InfluxDBClient
from models.anomaly_detector import AnomalyDetector
from models.diagnosis_model import DiagnosisModel
from collector.preprocess import FeatureExtractor  # 新增特征工程模块

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    logging.info("AIOps System Starting...")
    collector = NetworkCollector("192.168.1.1", "admin", "pass")
    db = InfluxDBClient()
    detector = AnomalyDetector()
    diagnoser = DiagnosisModel()
    extractor = FeatureExtractor(window_size=5)  # 5个采集周期的滑动窗口

    # 尝试加载已有模型，若无则使用模拟数据训练（实际应用中应从文件加载）
    if not detector.load_model('saved_models/iforest.pkl'):
        dummy_data = np.random.rand(100, 3)
        detector.train(dummy_data)
        diagnoser.train(dummy_data, np.random.randint(0, 3, 100))

    try:
        while True:
            try:
                # 1. 采集原始数据
                raw_data = collector.collect()
                if not raw_data:
                    logging.warning("Data collection failed, retrying...")
                    time.sleep(5)
                    continue

                # 2. 特征工程：生成滑动窗口统计特征
                features = extractor.transform([raw_data['cpu'], raw_data['mem'], raw_data['delay']])
                if features is None:
                    # 窗口未满，先存入基础数据，等待下一个周期
                    db.write_data(raw_data['cpu'], raw_data['mem'], raw_data['delay'], 0, "Normal")
                    time.sleep(5)
                    continue

                feature_array = np.array([features])

                # 3. 异常检测预测
                is_anomaly = detector.predict(feature_array)[0] == 1
                fault_type = "Normal"
                diag_log = ""

                # 4. 故障自动验证闭环
                if is_anomaly:
                    fault_type = diagnoser.predict(feature_array)[0]
                    logging.warning(f"Anomaly Detected! Predicted Fault: {fault_type}")

                    # 触发 Netmiko 自动执行对应诊断命令抓取现场日志
                    diag_log = collector.auto_diagnose(fault_type)
                    logging.info(f"Diagnostic Log Captured:\n{diag_log}")

                # 5. 存储全量数据及诊断证据
                db.write_data(raw_data['cpu'], raw_data['mem'], raw_data['delay'], int(is_anomaly), fault_type)

            except Exception as e:
                logging.error(f"Pipeline Error: {str(e)}")

            time.sleep(5)

    except KeyboardInterrupt:
        logging.info("System Stopped by User.")


if __name__ == "__main__":
    main()