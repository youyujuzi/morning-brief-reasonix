"""
统计建模模块 — 开盘锚点回归、置信区间、事件回溯
"""

import numpy as np
import pandas as pd
from scipy import stats


class OpeningAnchorModel:
    """
    A50 → 沪指开盘 线性回归模型
    
    公式: sh_open = alpha + beta * a50_change
    - beta: A50每涨1%，沪指开盘跟涨多少%
    - alpha: 开盘偏移量（无A50变动时的基准）
    - R²: 模型解释力
    """

    def __init__(self, hist_data: pd.DataFrame):
        """
        hist_data: DataFrame with columns [a50_change, sh_open_change]
        """
        self.hist_data = hist_data.dropna()
        self.N = len(self.hist_data)
        self.alpha = 0.0
        self.beta = 0.0
        self.r_squared = 0.0
        self.std_err = 0.0
        self.conf_interval = (0.0, 0.0)
        self._fit()

    def _fit(self):
        """执行线性回归"""
        if self.N < 5:
            return

        X = self.hist_data["a50_change"].values
        y = self.hist_data["sh_open_change"].values

        # OLS 回归
        slope, intercept, r_value, p_value, std_err = stats.linregress(X, y)

        self.alpha = round(intercept, 4)
        self.beta = round(slope, 4)
        self.r_squared = round(r_value ** 2, 4)
        self.std_err = round(std_err, 4)

        # 95% 置信区间
        if self.N > 2:
            t_val = stats.t.ppf(0.975, self.N - 2)
            margin = t_val * std_err
            self.conf_interval = (round(slope - margin, 4), round(slope + margin, 4))

    def predict(self, a50_change: float) -> dict:
        """
        根据 A50 隔夜涨跌预测沪指开盘
        
        返回:
        - predicted: 预测涨跌幅(%)
        - interval: 95%置信区间 (low, high)
        - confidence_level: 置信度评级
        """
        predicted = self.alpha + self.beta * a50_change

        # 置信区间（预测值 ± 标准误 * t值）
        if self.N > 2:
            t_val = stats.t.ppf(0.975, self.N - 2)
            se_pred = self.std_err * np.sqrt(
                1 + 1/self.N + (a50_change - self.hist_data["a50_change"].mean())**2
                / np.sum((self.hist_data["a50_change"] - self.hist_data["a50_change"].mean())**2)
            )
            margin = t_val * se_pred
            low = round(predicted - margin, 2)
            high = round(predicted + margin, 2)
        else:
            low = round(predicted - 0.5, 2)
            high = round(predicted + 0.5, 2)

        # 置信度评级
        if self.N >= 80 and self.r_squared > 0.5:
            level = "高"
        elif self.N >= 30 and self.r_squared > 0.3:
            level = "中"
        elif self.N >= 15:
            level = "低"
        else:
            level = "观察级"

        return {
            "predicted": round(predicted, 2),
            "interval": (low, high),
            "alpha": self.alpha,
            "beta": self.beta,
            "r_squared": self.r_squared,
            "N": self.N,
            "confidence_level": level,
        }

    def summary(self) -> str:
        """返回模型的文字摘要"""
        if self.N < 5:
            return "数据不足，无法建立回归模型"

        return (
            f"回归模型: 沪指开盘 = {self.alpha:+.4f} + {self.beta:.4f} × A50隔夜涨跌幅\n"
            f"R² = {self.r_squared:.4f}  |  N = {self.N} 个交易日\n"
            f"β 95%置信区间: ({self.conf_interval[0]:.4f}, {self.conf_interval[1]:.4f})"
        )


class EventMapper:
    """
    事件映射统计 — 美股异动 → A股映射标的 的历史回溯
    """

    @staticmethod
    def map_nvidia_to_a_share() -> str:
        """
        英伟达财报/重大异动对应的A股映射逻辑
        返回一段描述文字，供AI使用
        """
        return (
            "英伟达(NVDA)异动 → A股映射链:\n"
            "  直接映射: 光模块(中际旭创/新易盛/天孚通信)\n"
            "  间接映射: GPU服务器(浪潮信息)、PCB(沪电股份)\n"
            "  逻辑: AI算力需求↑ → 资本开支↑ → 光模块/服务器订单↑\n"
            "  风险: 该映射为明盘，近两次事件竞价均出现抢跑"
        )

    @staticmethod
    def map_tesla_to_a_share() -> str:
        return (
            "特斯拉(TSLA)异动 → A股映射链:\n"
            "  直接映射: 特斯拉供应链(拓普集团/旭升集团/三花智控)\n"
            "  逻辑: 销量/财报超预期 → 供应链订单预期上调\n"
            "  风险: 供应链个股常有独立走势，需结合自身技术面"
        )

    @staticmethod
    def map_apple_to_a_share() -> str:
        return (
            "苹果(AAPL)异动 → A股映射链:\n"
            "  直接映射: 苹果供应链(立讯精密/歌尔股份/蓝思科技)\n"
            "  逻辑: 新品周期/财报 → 供应链订单预期\n"
            "  风险: 苹果链个股近年来独立性增强，映射效应减弱"
        )

    @classmethod
    def get_all_mappings(cls) -> str:
        return "\n---\n".join([
            cls.map_nvidia_to_a_share(),
            cls.map_tesla_to_a_share(),
            cls.map_apple_to_a_share(),
        ])
