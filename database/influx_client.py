# database/influx_client.py

import configparser

from influxdb_client import InfluxDBClient as InfluxLibClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime


class InfluxDBClient:
    def __init__(self):
        """
        初始化数据库连接, 从 config.ini 读取配置
        """
        config = configparser.ConfigParser()
        config.read('config.ini')
        db_config = config['influxdb']

        self.client = InfluxLibClient(url=db_config.get('url'), 
                                     token=db_config.get('token'), 
                                     org=db_config.get('org'))
        self.bucket = db_config.get('bucket')
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()

    def query_latest_data(self, host="192.168.1.1"):
        """
        从 InfluxDB 查询最新的一条采集数据，按 host 过滤
        """
        query = f'''
        from(bucket: "{self.bucket}") 
        |> range(start: -1h) 
        |> filter(fn: (r) => r["_measurement"] == "network_metrics") 
        |> filter(fn: (r) => r["host"] == "{host}")
        |> last()
        '''
        try:
            tables = self.query_api.query(query, org=self.client.org)
            result = {}
            for table in tables:
                for record in table.records:
                    result[record.get_field()] = record.get_value()
            if result:
                print(f"成功获取设备 {host} 最新数据: CPU={result.get('cpu_usage')}%")
            return result
        except Exception as e:
            print(f"查询设备 {host} 失败: {e}")
            return None

    def query_timeseries(self, host="192.168.1.1", minutes=10, limit=300, fields=None):
        selected_fields = fields or [
            "cpu_usage",
            "mem_usage",
            "delay",
            "bandwidth_in_util",
            "bandwidth_out_util",
            "packet_loss_pct",
            "is_anomaly",
            "fault_type",
        ]
        field_filters = " or ".join([f'r["_field"] == "{f}"' for f in selected_fields])
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: -{int(minutes)}m)
        |> filter(fn: (r) => r["_measurement"] == "network_metrics")
        |> filter(fn: (r) => r["host"] == "{host}")
        |> filter(fn: (r) => {field_filters})
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: false)
        |> limit(n: {int(limit)})
        '''
        try:
            tables = self.query_api.query(query, org=self.client.org)
            series = []
            for table in tables:
                for record in table.records:
                    row = {"time": record.get_time().strftime("%Y-%m-%d %H:%M:%S")}
                    for f in selected_fields:
                        if f in record.values:
                            row[f] = record.values.get(f)
                    series.append(row)
            return series
        except Exception as e:
            print(f"查询时序数据失败: {e}")
            return []

    def query_anomaly_logs(self, limit=10, host=None):
        """
        查询最近的异常记录用于审计日志展示
        """
        host_filter = f'|> filter(fn: (r) => r["host"] == "{host}")' if host else ""
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: -24h)
        |> filter(fn: (r) => r["_measurement"] == "network_metrics")
        {host_filter}
        |> filter(fn: (r) => r["_field"] == "is_anomaly" or r["_field"] == "fault_type" or r["_field"] == "cpu_usage")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> filter(fn: (r) => r["is_anomaly"] == 1)
        |> sort(columns: ["_time"], desc: true)
        |> limit(n: {limit})
        '''
        try:
            tables = self.query_api.query(query, org=self.client.org)
            logs = []
            for table in tables:
                for record in table.records:
                    logs.append({
                        "time": record.get_time().strftime("%Y-%m-%d %H:%M:%S"),
                        "device": record.values.get("host", "Unknown"),
                        "val": f"{record.values.get('cpu_usage', 0)}%",
                        "type": record.values.get("fault_type", "未知异常"),
                        "level": "danger"
                    })
            return logs
        except Exception as e:
            print(f"查询异常日志失败: {e}")
            return []

    def query_recent_logs(self, limit=10, host=None):
        """查询最近的采集记录（包含正常/异常），用于前端审计日志展示"""
        host_filter = f'|> filter(fn: (r) => r["host"] == "{host}")' if host else ""
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: -24h)
        |> filter(fn: (r) => r["_measurement"] == "network_metrics")
        {host_filter}
        |> filter(fn: (r) => r["_field"] == "is_anomaly" or r["_field"] == "fault_type" or r["_field"] == "cpu_usage")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: true)
        |> limit(n: {limit})
        '''
        try:
            tables = self.query_api.query(query, org=self.client.org)
            logs = []
            for table in tables:
                for record in table.records:
                    is_anomaly = int(record.values.get("is_anomaly", 0) or 0)
                    fault_type = record.values.get("fault_type", "正常")
                    logs.append({
                        "time": record.get_time().strftime("%Y-%m-%d %H:%M:%S"),
                        "device": record.values.get("host", "Unknown"),
                        "val": f"{record.values.get('cpu_usage', 0)}%",
                        "type": fault_type if is_anomaly == 1 else "正常",
                        "level": "danger" if is_anomaly == 1 else "success"
                    })
            return logs
        except Exception as e:
            print(f"查询最近日志失败: {e}")
            return []

    def query_stats(self, host="192.168.1.1", hours=1):
        """
        查询最近 hours 小时内 CPU 的平均值与峰值
        """
        avg_query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: -{hours}h)
        |> filter(fn: (r) => r["_measurement"] == "network_metrics")
        |> filter(fn: (r) => r["host"] == "{host}")
        |> filter(fn: (r) => r["_field"] == "cpu_usage")
        |> mean()
        '''
        max_query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: -{hours}h)
        |> filter(fn: (r) => r["_measurement"] == "network_metrics")
        |> filter(fn: (r) => r["host"] == "{host}")
        |> filter(fn: (r) => r["_field"] == "cpu_usage")
        |> max()
        '''
        try:
            avg_tables = self.query_api.query(avg_query, org=self.client.org)
            max_tables = self.query_api.query(max_query, org=self.client.org)
            avg_val = None
            max_val = None
            for t in avg_tables:
                for r in t.records:
                    avg_val = r.get_value()
            for t in max_tables:
                for r in t.records:
                    max_val = r.get_value()
            return {"avg": avg_val, "max": max_val}
        except Exception as e:
            print(f"查询统计失败: {e}")
            return {"avg": None, "max": None}

    def write_data(
        self,
        cpu,
        mem,
        delay,
        is_anomaly,
        fault_type,
        host="192.168.1.1",
        bandwidth_in_util=None,
        bandwidth_out_util=None,
        packet_loss_pct=None,
    ):
        """
        【方法】：将采集到的数据点位写入 InfluxDB
        """
        try:
            point = Point("network_metrics") \
                .tag("host", host) \
                .field("cpu_usage", float(cpu)) \
                .field("mem_usage", float(mem)) \
                .field("delay", float(delay)) \
                .field("is_anomaly", int(is_anomaly)) \
                .field("fault_type", str(fault_type)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            if bandwidth_in_util is not None:
                point = point.field("bandwidth_in_util", float(bandwidth_in_util))
            if bandwidth_out_util is not None:
                point = point.field("bandwidth_out_util", float(bandwidth_out_util))
            if packet_loss_pct is not None:
                point = point.field("packet_loss_pct", float(packet_loss_pct))

            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            print(f"写入数据库失败: {e}")
            return False

    def save_metrics(self, data_dict):
        """
        【方法】：将采集到的字典数据转换为 InfluxDB 的点位并写入
        """
        try:
            point = Point(data_dict["measurement"]) \
                .tag("host", data_dict["tags"]["host"]) \
                .tag("vendor", data_dict["tags"]["vendor"]) \
                .time(data_dict["time"], WritePrecision.S)

            fields = data_dict.get("fields") or {}
            for key, value in fields.items():
                if value is None:
                    continue
                if isinstance(value, bool):
                    point = point.field(key, int(value))
                elif isinstance(value, int):
                    point = point.field(key, int(value))
                elif isinstance(value, float):
                    point = point.field(key, float(value))
                else:
                    point = point.field(key, str(value))

            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            print(f"写入数据库失败: {e}")
            return False
