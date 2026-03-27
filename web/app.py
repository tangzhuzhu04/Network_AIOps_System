import socket


# 解决中文计算机名编码问题
def getfqdn(name=''): return 'localhost'


socket.getfqdn = getfqdn

from flask import Flask, render_template, jsonify, request, make_response
import time
import json
import os
import sys

# 导入 InfluxDB 客户端，由于 web/app.py 在子目录，需要把根目录加入系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.influx_client import InfluxDBClient

app = Flask(__name__)
db = InfluxDBClient()

# 模拟设备列表与 IP 映射
DEVICE_MAP = {
    "Huawei-S5700": "192.168.1.1",
    "H3C-S5130": "192.168.1.2",
    "Home-Router": "192.168.1.3"
}
DEVICE_LIST = list(DEVICE_MAP.keys())


@app.route('/')
def index():
    return render_template('index.html', devices=DEVICE_LIST)


@app.route('/api/metrics')
def get_metrics():
    device_name = request.args.get('device', DEVICE_LIST[0])
    target_ip = DEVICE_MAP.get(device_name, "192.168.1.1")
    
    # 尝试从 InfluxDB 获取真实数据 (增加 host 过滤)
    real_data = db.query_latest_data(host=target_ip)
    
    if real_data and 'cpu_usage' in real_data:
        cpu_val = real_data.get('cpu_usage', 0)
        is_anomaly = real_data.get('is_anomaly', 0)
        fault_type = real_data.get('fault_type', "正常")
        
        status = "异常" if is_anomaly == 1 else "正常"
        diagnosis = f"AI判定: {fault_type}"
        suggestion = "建议立即检查设备。" if status == "异常" else "系统运行平稳。"
    else:
        # 更加明显的提示
        cpu_val = 0.0 
        status = "连接中"
        diagnosis = "数据库尚未接收到数据..."
        suggestion = "请确认 main.py 正在运行且数据库中有记录。"

    return jsonify({
        "time": time.strftime("%H:%M:%S"),
        "cpu": cpu_val,
        "status": status,
        "diagnosis": diagnosis,
        "suggestion": suggestion
    })


@app.route('/api/logs')
def get_logs():
    device_name = request.args.get('device', DEVICE_LIST[0])
    target_ip = DEVICE_MAP.get(device_name, "192.168.1.1")

    # 返回最近的采集记录（包含正常/异常），这样“当前正常”与“历史异常”能同时看到
    logs = db.query_recent_logs(limit=10, host=target_ip)

    if not logs:
        logs = [{"time": time.strftime("%Y-%m-%d %H:%M:%S"), "device": target_ip, "val": "-", "type": "暂无记录", "level": "success"}]

    return jsonify(logs)


@app.route('/api/export_report')
def export_report():
    device = request.args.get('device', DEVICE_LIST[0])
    target_ip = DEVICE_MAP.get(device, "192.168.1.1")

    latest = db.query_latest_data(host=target_ip) or {}
    stats = db.query_stats(host=target_ip, hours=1)

    avg_val = stats.get("avg")
    peak_val = stats.get("max")
    avg_load = f"{avg_val:.1f}%" if isinstance(avg_val, (int, float)) else "N/A"
    peak_load = f"{peak_val:.1f}%" if isinstance(peak_val, (int, float)) else "N/A"

    is_anomaly = latest.get("is_anomaly", 0)
    fault_type = latest.get("fault_type", "未知")
    status_text = "异常" if is_anomaly == 1 else "良好"

    report_template = f"""
================================================
       小型网络智能运维系统 - 自动化诊断报告
================================================
生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
受测设备: {device}
------------------------------------------------
一、 运行指标统计 (过去 1 小时)
1. 平均负载: {avg_load}
2. 峰值负载: {peak_load}
3. 状态评定: {status_text}

二、 AI 诊断结论
[核心预测模块]: 孤立森林算法检测到时序数据分布异常。
[根因识别模块]: 随机森林判定故障类型为“{fault_type}”。

三、 专家处置建议
1. 检查 SNMP/SSH 采集频率是否过高。
2. 核对接口流量是否存在突发大报文。
3. 建议执行：display interface brief 查看错包计数。
------------------------------------------------
报告生成器版本: v1.0 (AI Ops Engine)
"""
    response = make_response(report_template)
    response.headers["Content-Disposition"] = f"attachment; filename=Diagnosis_{device}.txt"
    return response


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
