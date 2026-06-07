"""MCP Server 独立测试脚本。

验证 MCP 服务端能否正常启动、暴露工具、并响应调用。
用法：python test_mcp_server.py
"""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_server():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server/server.py"],
    )

    print("正在启动 MCP Server ...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("MCP Server 连接成功!\n")

            # 列出所有工具
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            print(f"可用工具 ({len(tool_names)}): {tool_names}\n")

            # 测试 get_user_id
            result = await session.call_tool("get_user_id", {})
            print(f"[get_user_id] => {result.content[0].text}")

            # 测试 get_current_month
            result = await session.call_tool("get_current_month", {})
            print(f"[get_current_month] => {result.content[0].text}")

            # 测试 fill_context_for_report
            result = await session.call_tool("fill_context_for_report", {})
            print(f"[fill_context_for_report] => {result.content[0].text}")

            # 测试 rag_summarize
            result = await session.call_tool("rag_summarize", {"query": "扫地机器人滤网更换"})
            print(f"[rag_summarize] => {result.content[0].text[:200]}...")

            # 测试 fetch_external_data
            result = await session.call_tool("fetch_external_data", {"user_id": "1001", "month": "2025-01"})
            print(f"[fetch_external_data] => {result.content[0].text}")

            print("\n所有工具测试通过!")


if __name__ == "__main__":
    asyncio.run(test_server())
