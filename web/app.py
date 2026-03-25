import socket


# 解决中文计算机名编码问题
def getfqdn(name=''): return 'localhost'


socket.getfqdn = getfqdn

from flask import Flask, render_template, jsonify, request, make_response
import time
import json

app = Flask(__name__)

# 模拟数据库与AI诊断库 (实际应调用你之前的 InfluxDBManager 和 AnomalyDetector)
DEVICE_LIST = ["Huawei-S5700", "H3C-S5130", "Home-Router"]


@app.route('/')
def index():
    return render_template('index.html', devices=DEVICE_LIST)


@app.route('/api/metrics')
def get_metrics():
    device = request.args.get('device', DEVICE_LIST[0])
    # 模拟真实采集数据与AI预测结果
    cpu_val = 20 + (10 if "Huawei" in device else 5)
    status = "正常" if cpu_val < 80 else "异常"

    return jsonify({
        "time": time.strftime("%H:%M:%S"),
        "cpu": cpu_val,
        "status": status,
        "diagnosis": "链路负载正常" if status == "正常" else "检测到突发流量拥堵",
        "suggestion": "无需操作" if status == "正常" else "建议检查端口 Gi0/0/1 流量统计，验证 ACL 策略。"
    })


@app.route('/api/logs')
def get_logs():
    # 模拟从 InfluxDB 查询过去的历史记录
    logs = [
        {"time": "2026-02-27 19:45:01", "device": "Huawei-S5700", "val": "88%", "type": "高负载", "level": "danger"},
        {"time": "2026-02-27 18:30:12", "device": "H3C-S5130", "val": "12%", "type": "正常", "level": "success"}
    ]
    return jsonify(logs)


@app.route('/api/export_report')
def export_report():
    device = request.args.get('device', 'Unknown-Device')
    # 模拟从数据库获取统计信息，增加报告的专业性
    avg_load = "24.5%"
    peak_load = "88.2%"

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
3. 状态评定: {'异常' if float(peak_load.strip('%')) > 80 else '良好'}

二、 AI 诊断结论
[核心预测模块]: 孤立森林算法检测到时序数据分布异常。
[根因识别模块]: 随机森林判定故障类型为“突发带宽拥堵”。

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