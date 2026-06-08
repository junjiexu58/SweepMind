import os
import sys

# 确保项目根目录在 sys.path 中，使项目内的相对导入正常工作
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from mcp.server.fastmcp import FastMCP
from agent.tools.tool_impl import (
    query_weather, query_rag, get_random_user_id, get_random_month, fetch_user_record,
)

mcp_server = FastMCP("sweepmind-tools")


@mcp_server.tool()
def get_weather(user_query: str) -> str:
    """根据用户原始问题提取城市并查询实时天气。

    Args:
        user_query: 用户关于天气的原始问题
    """
    return query_weather(user_query)


@mcp_server.tool()
def rag_summarize(query: str) -> str:
    """从向量存储中检索参考资料。

    Args:
        query: 检索词，贴合用户问题的核心关键词
    """
    return query_rag(query)


@mcp_server.tool()
def get_user_id() -> str:
    """获取用户的ID，以纯字符串形式返回。"""
    return get_random_user_id()


@mcp_server.tool()
def get_current_month() -> str:
    """获取当前月份，以纯字符串形式返回。"""
    return get_random_month()


@mcp_server.tool()
def fetch_external_data(user_id: str, month: str) -> str:
    """从外部系统中获取指定用户在指定月份的使用记录。

    Args:
        user_id: 用户ID，数字字符串（如"1001"）
        month: 月份，格式为YYYY-MM（如"2025-06"）
    """
    return fetch_user_record(user_id, month)


@mcp_server.tool()
def fill_context_for_report() -> str:
    """调用后触发报告生成模式的上下文切换。

    无入参，返回一个信号标记，客户端检测到该标记后切换到报告生成提示词。
    """
    return '{"__mcp_signal__": "report_mode"}'


if __name__ == "__main__":
    mcp_server.run(transport="stdio")
