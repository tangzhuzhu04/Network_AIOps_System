# database/influx_client.py

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS


class InfluxDBManager:
    def __init__(self, token, org, bucket, url="http://localhost:8086"):
        """
        初始化数据库连接
        """
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.bucket = bucket
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def save_metrics(self, data_dict):
        """
        【方法】：将采集到的字典数据转换为 InfluxDB 的点位并写入
        """
        try:
            point = Point(data_dict["measurement"]) \
                .tag("host", data_dict["tags"]["host"]) \
                .tag("vendor", data_dict["tags"]["vendor"]) \
                .field("cpu_usage", data_dict["fields"]["cpu_usage"]) \
                .field("mem_usage", data_dict["fields"]["mem_usage"]) \
                .time(data_dict["time"], WritePrecision.S)

            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            print(f"写入数据库失败: {e}")
            return False