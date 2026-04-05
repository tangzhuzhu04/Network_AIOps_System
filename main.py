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
    use_ai_logic = config.getboolean("pipeline", "use_ai_logic", fallback=False)
    ping_src = config.get("mininet", "ping_src", fallback="pc1")
    ping_dst = device_config.get("gateway_ip", fallback=None)

    collector = NetworkCollector(device_config.get('ip'), 
                               device_config.get('user'), 
                               device_config.get('password'),
                               gateway_ip=ping_dst,
                               ping_src=ping_src,
                               use_ai_logic=use_ai_logic)
    
    # Mininet 节点
    virtual_devices = [
        {"id": "s1", "name": "Core-Switch"},
        {"id": "s2", "name": "Office-Access"},
        {"id": "s3", "name": "Server-Access"},
    ]
    collectors = [
        NetworkCollector(
            d["id"],
            device_config.get("user"),
            device_config.get("password"),
            gateway_ip=ping_dst,
            ping_src=ping_src,
            use_ai_logic=use_ai_logic,
        )
        for d in virtual_devices
    ]
    
    db = InfluxDBClient()
    detector = AnomalyDetector()
    diagnoser = DiagnosisModel()
    # 每个设备单独维护特征提取器，避免设备之间相互影响
    extractor_map = {}
    consecutive_anomaly = {}

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

                    delay_val = raw_data.get("avg_delay_ms", raw_data.get("delay", 0))
                    bw_in = raw_data.get("bandwidth_in_util", None)
                    bw_out = raw_data.get("bandwidth_out_util", None)
                    loss = raw_data.get("packet_loss_pct", None)

                    if not collector.use_ai_logic:
                        is_anomaly = int(raw_data.get("is_anomaly", 0) or 0)
                        fault_type = raw_data.get("fault_type", "Normal")
                        logging.info(
                            f"Device {collector.ip} raw metrics -> CPU:{raw_data['cpu']} MEM:{raw_data['mem']} "
                            f"DELAY:{delay_val} BW_IN:{bw_in} BW_OUT:{bw_out} LOSS:{loss}"
                        )
                    else:
                        # 2. 特征工程：生成滑动窗口统计特征
                        if collector.ip not in extractor_map:
                            extractor_map[collector.ip] = FeatureExtractor(window_size=5)
                        features = extractor_map[collector.ip].transform([raw_data['cpu'], raw_data['mem'], delay_val])
                        logging.info(
                            f"Device {collector.ip} raw metrics -> CPU:{raw_data['cpu']} MEM:{raw_data['mem']} "
                            f"DELAY:{delay_val} BW_IN:{bw_in} BW_OUT:{bw_out} LOSS:{loss}"
                        )
                        if features is None:
                            db.write_data(
                                raw_data["cpu"],
                                raw_data["mem"],
                                delay_val,
                                0,
                                "Normal",
                                host=collector.ip,
                                bandwidth_in_util=bw_in,
                                bandwidth_out_util=bw_out,
                                packet_loss_pct=loss,
                            )
                            continue

                        feature_array = np.array([features])

                        # 3. 异常检测预测 + 规则兜底
                        is_anomaly = detector.predict(feature_array) == 1

                        rule_fault = None
                        if raw_data["cpu"] > 70:
                            is_anomaly = True
                            rule_fault = "High_CPU"
                        elif delay_val > 80:
                            is_anomaly = True
                            rule_fault = "High_Delay"
                        elif (loss is not None) and float(loss) > 1.0:
                            is_anomaly = True
                            rule_fault = "Packet_Loss"

                        fault_type = "Normal"
                        if is_anomaly:
                            fault_type = rule_fault or diagnoser.predict(feature_array)[0]
                            logging.warning(f"Device {collector.ip} Anomaly! Predicted: {fault_type}")

                    key = collector.ip
                    cnt = consecutive_anomaly.get(key, 0)
                    if int(is_anomaly) == 1:
                        cnt += 1
                    else:
                        cnt = 0
                    consecutive_anomaly[key] = cnt

                    effective_is_anomaly = 1 if cnt >= 2 else 0
                    if effective_is_anomaly == 0:
                        fault_type = "Normal"
                    else:
                        if cnt == 2:
                            collector.auto_diagnose(fault_type)

                    # 5. 存储全量数据
                    db.write_data(
                        raw_data["cpu"],
                        raw_data["mem"],
                        delay_val,
                        int(effective_is_anomaly),
                        fault_type,
                        host=collector.ip,
                        bandwidth_in_util=bw_in,
                        bandwidth_out_util=bw_out,
                        packet_loss_pct=loss,
                    )
                    logging.info(
                        f"Device {collector.ip} write -> CPU:{raw_data['cpu']} is_anomaly:{int(effective_is_anomaly)} "
                        f"fault:{fault_type} BW_IN:{bw_in} BW_OUT:{bw_out} LOSS:{loss}"
                    )

                except Exception as e:
                    logging.error(f"Pipeline Error on {collector.ip}: {str(e)}")

            time.sleep(2) # 缩短采集间隔，让图表动得更快

    except KeyboardInterrupt:
        logging.info("System Stopped by User.")


if __name__ == "__main__":
    main()
