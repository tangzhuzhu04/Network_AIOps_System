 # models/anomaly_detector.py
from pyod.models.iforest import IForest
import joblib
import os

class AnomalyDetector:
    """
    对应开题报告：机器学习模型构建模块
    功能：基于孤立森林算法训练异常检测模型并进行实时预警
    """
    def __init__(self, contamination=0.1):
        """
        初始化模型
        :param contamination: 异常比例（预警敏感度），默认为 10%
        """
        # n_estimators: 树的数量；contamination: 开题报告提到的关键超参数
        self.model = IForest(n_estimators=100,
                             contamination=contamination,
                             random_state=42,
                             n_jobs=-1) # 使用多核提升运行效率

    def train(self, features):
        """
        训练模型：学习正常网络状态的基准特征
        :param features: 经过预处理的特征矩阵（如 CPU、内存、滑动均值等）
        """
        self.model.fit(features)
        print("【模型训练】异常检测模型（IForest）训练完成 ")

    def predict(self, current_feature):
        """
        实时预测：判断当前数据是否偏离正常基准
        :param current_feature: 当前采集并处理后的特征向量
        :return: 0 为正常，1 为异常（预警触发点）
        """
        # 将输入转换为模型要求的二维数组格式
        prediction = self.model.predict(current_feature.reshape(1, -1))
        return int(prediction[0])

    def save_model(self, model_path='models/saved_models/iforest_v1.pkl'):
        """保存训练好的模型文件 """
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(self.model, model_path)
        print(f"模型已保存至: {model_path}")

    def load_model(self, model_path):
        """加载已有的模型 """
        if not os.path.exists(model_path):
            print(f"模型文件不存在: {model_path}")
            return False
        try:
            self.model = joblib.load(model_path)
            print("模型加载成功")
            return True
        except Exception as e:
            print(f"加载模型失败: {e}")
            return False