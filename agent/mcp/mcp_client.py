import sys

from langchain_mcp_adapters.client import MultiServerMCPClient

from utils.path_tool import get_abs_path


async def create_mcp_client() -> MultiServerMCPClient:
    """创建并连接到 MCP 服务端，返回已挂载工具的客户端。"""
    server_script = get_abs_path("agent/mcp/server.py")

    client = MultiServerMCPClient(
        {
            "sweepmind": {
                "command": sys.executable,
                "args": [server_script],
                "transport": "stdio",
            }
        }
    )

    await client.__aenter__()
    return client
