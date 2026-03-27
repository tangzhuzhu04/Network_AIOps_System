# main.py
import time
import logging
import numpy as np
import configparser
from collector.ssh_collector import NetworkCollector
from database.influx_client import InfluxDBClient
from models.anomaly_detector import AnomalyDetector
from models.diagnosis_model import DiagnosisModel
from collector.preprocess import FeatureExtractor  # 新增特征工程模块

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    logging.info("AIOps System Starting...")
    
    # 从 config.ini 读取配置
    config = configparser.ConfigParser()
    config.read('config.ini')
    device_config = config['network_device']

    collector = NetworkCollector(device_config.get('ip'), 
                               device_config.get('user'), 
                               device_config.get('password'))
    
    # 定义多个模拟设备 IP
    virtual_devices = [
        {"ip": "192.168.1.1", "name": "Huawei-S5700"},
        {"ip": "192.168.1.2", "name": "H3C-S5130"},
        {"ip": "192.168.1.3", "name": "Home-Router"}
    ]
    collectors = [NetworkCollector(d['ip'], "admin", "pass") for d in virtual_devices]
    
    db = InfluxDBClient()
    detector = AnomalyDetector()
    diagnoser = DiagnosisModel()
    # 每个设备单独维护特征提取器，避免设备之间相互影响
    extractor_map = {}

    # 尝试加载已有模型，若无则使用模拟数据训练（实际应用中应从文件加载）
    model_path = 'saved_models/iforest.pkl'
    if not detector.load_model(model_path):
        dummy_data = np.random.rand(100, 3)
        detector.train(dummy_data)
        diagnoser.train(dummy_data, np.random.randint(0, 3, 100))
        # 训练完保存，避免下次还报“模型不存在”
        detector.save_model(model_path)
        diagnoser.save('saved_models/rf_diagnosis.pkl')

    try:
        while True:
            for i, collector in enumerate(collectors):
                try:
                    # 1. 采集原始数据
                    raw_data = collector.collect()
                    if not raw_data:
                        logging.warning(f"Device {collector.ip} collection failed.")
                        continue

                    # 2. 特征工程：生成滑动窗口统计特征
                    if collector.ip not in extractor_map:
                        extractor_map[collector.ip] = FeatureExtractor(window_size=5)
                    features = extractor_map[collector.ip].transform([raw_data['cpu'], raw_data['mem'], raw_data['delay']])
                    logging.info(f"Device {collector.ip} raw metrics -> CPU:{raw_data['cpu']} MEM:{raw_data['mem']} DELAY:{raw_data['delay']}")
                    if features is None:
                        # 窗口未满，先存入基础数据
                        db.write_data(raw_data['cpu'], raw_data['mem'], raw_data['delay'], 0, "Normal", host=collector.ip)
                        continue

                    feature_array = np.array([features])

                    # 3. 异常检测预测 + 规则兜底
                    is_anomaly = detector.predict(feature_array) == 1

                    # 基于实时原始值的规则增强，确保演示可见
                    rule_fault = None
                    if raw_data['cpu'] > 70:
                        is_anomaly = True
                        rule_fault = "High_CPU"
                    elif raw_data['delay'] > 80:
                        is_anomaly = True
                        rule_fault = "High_Delay"

                    fault_type = "Normal"
                    if is_anomaly:
                        # 若规则触发则优先采用规则类型，否则走模型诊断
                        fault_type = rule_fault or diagnoser.predict(feature_array)[0]
                        logging.warning(f"Device {collector.ip} Anomaly! Predicted: {fault_type}")
                        collector.auto_diagnose(fault_type)

                    # 5. 存储全量数据
                    db.write_data(raw_data['cpu'], raw_data['mem'], raw_data['delay'], int(is_anomaly), fault_type, host=collector.ip)
                    logging.info(f"Device {collector.ip} write -> CPU:{raw_data['cpu']} is_anomaly:{int(is_anomaly)} fault:{fault_type}")

                except Exception as e:
                    logging.error(f"Pipeline Error on {collector.ip}: {str(e)}")

            time.sleep(2) # 缩短采集间隔，让图表动得更快

    except KeyboardInterrupt:
        logging.info("System Stopped by User.")


if __name__ == "__main__":
    main()
