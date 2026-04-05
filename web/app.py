import socket


# 解决中文计算机名编码问题
def getfqdn(name=''): return 'localhost'


socket.getfqdn = getfqdn

from flask import Flask, render_template, jsonify, request, make_response
import time
import json
import os
import sys
import configparser

# 导入 InfluxDB 客户端，由于 web/app.py 在子目录，需要把根目录加入系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.influx_client import InfluxDBClient

app = Flask(__name__)
db = InfluxDBClient()

DEVICE_LIST = [
    {"id": "s1", "label": "核心交换机 (s1)"},
    {"id": "s2", "label": "办公区接入 (s2)"},
    {"id": "s3", "label": "服务器区接入 (s3)"},
]
DEVICE_MAP = {d["id"]: d["id"] for d in DEVICE_LIST}


@app.route('/')
def index():
    config = configparser.ConfigParser()
    config.read("config.ini")
    topology_url = config.get("topology", "url", fallback="http://192.168.17.128:5000/")
    return render_template('index.html', devices=DEVICE_LIST, topology_url=topology_url)


@app.route('/api/metrics')
def get_metrics():
    default_device = DEVICE_LIST[0]["id"]
    device_id = request.args.get('device', default_device)
    target_host = DEVICE_MAP.get(device_id, default_device)
    
    try:
        real_data = db.query_latest_data(host=target_host)
    except Exception:
        real_data = None
    
    if real_data and 'cpu_usage' in real_data:
        cpu_val = real_data.get('cpu_usage', 0)
        mem_val = real_data.get('mem_usage', 0)
        delay_val = real_data.get('delay', 0)
        bw_in = real_data.get('bandwidth_in_util', 0)
        bw_out = real_data.get('bandwidth_out_util', 0)
        loss = real_data.get('packet_loss_pct', 0)
        is_anomaly = int(real_data.get('is_anomaly', 0) or 0)
        fault_type = real_data.get('fault_type', "正常")
        
        status = "异常" if is_anomaly == 1 else "正常"
        diagnosis = f"判定: {fault_type}"
        suggestion = "建议立即检查设备。" if status == "异常" else "系统运行平稳。"
    else:
        # 更加明显的提示
        cpu_val = 0.0 
        mem_val = 0.0
        delay_val = 0.0
        bw_in = 0.0
        bw_out = 0.0
        loss = 0.0
        is_anomaly = 0
        fault_type = "Normal"
        status = "连接中"
        diagnosis = "数据库尚未接收到数据..."
        suggestion = "请确认 main.py 正在运行且数据库中有记录。"

    return jsonify({
        "time": time.strftime("%H:%M:%S"),
        "cpu": cpu_val,
        "mem": mem_val,
        "delay": delay_val,
        "bandwidth_in_util": bw_in,
        "bandwidth_out_util": bw_out,
        "packet_loss_pct": loss,
        "bw_in": bw_in,
        "bw_out": bw_out,
        "loss": loss,
        "is_anomaly": int(is_anomaly or 0),
        "fault_type": fault_type,
        "status": status,
        "diagnosis": diagnosis,
        "suggestion": suggestion
    })


@app.route("/api/timeseries")
def get_timeseries():
    default_device = DEVICE_LIST[0]["id"]
    device_id = request.args.get("device", default_device)
    target_host = DEVICE_MAP.get(device_id, default_device)
    minutes = int(request.args.get("minutes", 10))
    limit = int(request.args.get("limit", 300))
    fields_arg = request.args.get("fields", "")
    fields = [f.strip() for f in fields_arg.split(",") if f.strip()] or None
    series = db.query_timeseries(host=target_host, minutes=minutes, limit=limit, fields=fields)
    return jsonify(series)


@app.route('/api/logs')
def get_logs():
    default_device = DEVICE_LIST[0]["id"]
    device_id = request.args.get('device', default_device)
    target_host = DEVICE_MAP.get(device_id, default_device)

    # 返回最近的采集记录（包含正常/异常），这样“当前正常”与“历史异常”能同时看到
    logs = db.query_recent_logs(limit=10, host=target_host)

    if not logs:
        logs = [{"time": time.strftime("%Y-%m-%d %H:%M:%S"), "device": target_host, "val": "-", "type": "暂无记录", "level": "success"}]

    return jsonify(logs)


@app.route('/api/export_report')
def export_report():
    default_device = DEVICE_LIST[0]["id"]
    device_id = request.args.get('device', default_device)
    target_host = DEVICE_MAP.get(device_id, default_device)

    latest = db.query_latest_data(host=target_host) or {}
    stats = db.query_stats(host=target_host, hours=1)

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
受测设备: {device_id}
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
    safe_device = "".join(ch for ch in str(device_id) if ch.isalnum() or ch in ("-", "_")) or "device"
    response.headers["Content-Disposition"] = f"attachment; filename=Diagnosis_{safe_device}.txt"
    return response


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
