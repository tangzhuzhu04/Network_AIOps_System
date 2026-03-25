# collector/preprocess.py
import pandas as pd


class DataPreprocessor:
    """
    对应开题报告：数据预处理模块
    """

    def __init__(self, window_size=5):
        self.window_size = window_size

    def process_metrics(self, raw_data_list):
        """
        处理采集到的原始列表数据
        """
        df = pd.DataFrame(raw_data_list)

        # 1. 数据清洗：处理缺失值（插值法）
        df['cpu_usage'] = df['cpu_usage'].interpolate().fillna(method='bfill')

        # 2. 异常值处理：3σ 原则
        mean = df['cpu_usage'].mean()
        std = df['cpu_usage'].std()
        df.loc[abs(df['cpu_usage'] - mean) > 3 * std, 'cpu_usage'] = mean

        # 3. 特征工程：滑动窗口均值
        df['cpu_rolling_mean'] = df['cpu_usage'].rolling(window=self.window_size).mean()

        return df.fillna(0)