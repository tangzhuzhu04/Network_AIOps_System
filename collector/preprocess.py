# collector/preprocess.py
import pandas as pd
import numpy as np


class DataPreprocessor:
    """对应开题报告：数据预处理模块 (用于批量处理)"""

    def __init__(self, window_size=5):
        self.window_size = window_size

    def process_metrics(self, raw_data_list):
        df = pd.DataFrame(raw_data_list)
        # 兼容 Pandas 新版本的写法
        df['cpu_usage'] = df['cpu_usage'].interpolate().bfill()
        mean = df['cpu_usage'].mean()
        std = df['cpu_usage'].std()
        if std > 0:
            df.loc[abs(df['cpu_usage'] - mean) > 3 * std, 'cpu_usage'] = mean
        df['cpu_rolling_mean'] = df['cpu_usage'].rolling(window=self.window_size).mean()
        return df.fillna(0)


class FeatureExtractor:
    """对应开题报告：特征工程模块 (用于 main.py 实时流)"""

    def __init__(self, window_size=5):
        self.window_size = window_size
        self.buffer = []

    def transform(self, new_data):
        """将采集的 [cpu, mem, delay] 转换为平滑后的特征"""
        self.buffer.append(new_data)
        if len(self.buffer) < self.window_size:
            return None
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)

        # 计算滑动窗口均值，作为 AIOps 预测的输入
        return np.mean(np.array(self.buffer), axis=0)