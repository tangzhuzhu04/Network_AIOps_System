# models/diagnosis_model.py
from sklearn.ensemble import RandomForestClassifier
import joblib
import sys

class DiagnosisModel:
    """
    对应开题报告：故障诊断模型构建，输出故障类型及根因
    """
    def __init__(self):
        # 使用随机森林分类模型
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        # 故障类型映射表，方便非专业人员理解
        self.label_map = {0: "正常", 1: "带宽拥堵", 2: "端口故障", 3: "路由配置错误"}

    def train(self, X_train, y_train):
        """
        X_train: 特征数据（CPU、丢包率等）
        y_train: 故障标签（0, 1, 2, 3）
        """
        self.model.fit(X_train, y_train)
        sys.stdout.write("Model trained: DiagnosisModel(RandomForest)\n")

    def predict(self, feature_data):
        """输入异常特征，输出诊断结论，与 diagnose 方法保持一致以适配 main.py"""
        # 兼容 main.py 里的 [0] 调用方式
        res = self.diagnose(feature_data)
        return [res]

    def diagnose(self, feature_data):
        """输入异常特征，输出诊断结论 """
        label = self.model.predict(feature_data.reshape(1, -1))[0]
        return self.label_map.get(label, "未知故障")

    def save(self, path="models/rf_diagnosis.pkl"):
        joblib.dump(self.model, path)
