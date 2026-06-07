import os
import sys

# 确保项目根目录在 sys.path 中，使项目内的相对导入正常工作
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from mcp.server.fastmcp import FastMCP

from model.factory import chat_model
from rag.rag_service import RagSummarizeService
from utils.config_handler import agent_conf
from utils.logger_handler import logger
from utils.path_tool import get_abs_path
from utils.qweather import QW_LANG, extract_city_info, lookup_location_id, qweather_get

import random

mcp_server = FastMCP("sweepmind-tools")

# 初始化共享资源
rag_service = RagSummarizeService()

user_ids = ["1001", "1002", "1003", "1004", "1005", "1006", "1007", "1008", "1009", "1010"]
month_arr = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
             "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"]
external_data: dict = {}


def _generate_external_data():
    if not external_data:
        external_data_path = get_abs_path(agent_conf["external_data_path"])

        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件{external_data_path}不存在")

        with open(external_data_path, "r", encoding="utf-8") as f:
            for line in f.readlines()[1:]:
                arr: list[str] = line.strip().split(",")

                user_id: str = arr[0].replace('"', "")
                feature: str = arr[1].replace('"', "")
                efficiency: str = arr[2].replace('"', "")
                consumables: str = arr[3].replace('"', "")
                comparison: str = arr[4].replace('"', "")
                time: str = arr[5].replace('"', "")

                if user_id not in external_data:
                    external_data[user_id] = {}

                external_data[user_id][time] = {
                    "特征": feature,
                    "效率": efficiency,
                    "耗材": consumables,
                    "对比": comparison,
                }


@mcp_server.tool()
def get_weather(user_query: str) -> str:
    """根据用户原始问题提取城市并查询实时天气。

    Args:
        user_query: 用户关于天气的原始问题
    """
    if not user_query or not user_query.strip():
        return "未提供查询内容，无法查询天气"

    city_text = extract_city_info(user_query.strip())
    if not city_text:
        return "我没有从你的问题里识别出城市，请直接告诉我城市名，例如：杭州、苏州、北京。"

    try:
        resolved_city, location_id = lookup_location_id(city_text)

        weather = qweather_get(
            "/v7/weather/now",
            {
                "location": location_id,
                "lang": QW_LANG,
            },
        )
        if weather.get("code") != "200" or not weather.get("now"):
            return f"{resolved_city}天气查询失败"

        now = weather["now"]
        return (
            f"{resolved_city}当前天气{now.get('text', '未知')}，"
            f"气温{now.get('temp', '未知')}℃，"
            f"体感{now.get('feelsLike', '未知')}℃，"
            f"湿度{now.get('humidity', '未知')}%，"
            f"{now.get('windDir', '未知')}{now.get('windScale', '未知')}级，"
            f"观测时间{now.get('obsTime', '未知')}。"
        )
    except Exception as e:
        logger.error(f"[get_weather]天气查询失败 user_query={user_query} err={str(e)}")
        return "天气查询失败，请稍后重试。"


@mcp_server.tool()
def rag_summarize(query: str) -> str:
    """从向量存储中检索参考资料。

    Args:
        query: 检索词，贴合用户问题的核心关键词
    """
    return rag_service.rag_summarize(query)


@mcp_server.tool()
def get_user_id() -> str:
    """获取用户的ID，以纯字符串形式返回。"""
    return random.choice(user_ids)


@mcp_server.tool()
def get_current_month() -> str:
    """获取当前月份，以纯字符串形式返回。"""
    return random.choice(month_arr)


@mcp_server.tool()
def fetch_external_data(user_id: str, month: str) -> str:
    """从外部系统中获取指定用户在指定月份的使用记录。

    Args:
        user_id: 用户ID，数字字符串（如"1001"）
        month: 月份，格式为YYYY-MM（如"2025-06"）
    """
    _generate_external_data()

    try:
        return str(external_data[user_id][month])
    except KeyError:
        logger.warning(f"[fetch_external_data]未能检索到用户：{user_id}在{month}的使用记录数据")
        return ""


@mcp_server.tool()
def fill_context_for_report() -> str:
    """调用后触发报告生成模式的上下文切换。

    无入参，返回一个信号标记，客户端检测到该标记后切换到报告生成提示词。
    """
    return '{"__mcp_signal__": "report_mode"}'


if __name__ == "__main__":
    mcp_server.run(transport="stdio")
