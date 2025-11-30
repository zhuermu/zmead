"""
Base analyzer abstract class for performance analysis.
"""

from abc import ABC, abstractmethod


class BaseAnalyzer(ABC):
    """分析器基类"""

    @abstractmethod
    async def analyze(self, data: dict, context: dict) -> dict:
        """
        分析数据

        Args:
            data: 输入数据
            context: 上下文信息

        Returns:
            分析结果
        """
        pass
