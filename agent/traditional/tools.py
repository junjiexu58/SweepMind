from langchain_core.tools import tool
from agent.tools.tool_impl import (
    query_weather, query_rag, get_random_user_id, get_random_month, fetch_user_record,
)


@tool(description="根据用户原始问题提取城市并查询实时天气")
def get_weather(user_query: str) -> str:
    return query_weather(user_query)


@tool(description="从向量存储中检索参考资料")
def rag_summarize(query: str) -> str:
    return query_rag(query)


@tool(description="获取用户的ID，以纯字符串形式返回")
def get_user_id() -> str:
    return get_random_user_id()


@tool(description="获取当前月份，以纯字符串形式返回")
def get_current_month() -> str:
    return get_random_month()


@tool(description="从外部系统中获取指定用户在指定月份的使用记录，以纯字符串形式返回， 如果未检索到返回空字符串")
def fetch_external_data(user_id: str, month: str) -> str:
    return fetch_user_record(user_id, month)


@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    return "fill_context_for_report已调用"
