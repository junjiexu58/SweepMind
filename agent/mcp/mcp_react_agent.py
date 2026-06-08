import asyncio
import queue
import sys
import threading

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from agent.mcp.mcp_middleware import MCPMiddlewareManager
from model.factory import chat_model
from utils.path_tool import get_abs_path


class MCPReactAgent:
    """基于 MCP 工具的 ReAct Agent，对外暴露与原 ReactAgent 相同的 execute_stream 接口。"""

    def __init__(self):
        self.middleware = MCPMiddlewareManager()
        self._loop = asyncio.new_event_loop()
        self._started = threading.Event()
        self._client = None
        self._agent = None
        self._pending_tool_args: dict = {}

        # 在后台守护线程中运行事件循环，保持 MCP 子进程连接存活
        self._bg_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._bg_thread.start()
        self._started.wait()

    def _run_event_loop(self):
        asyncio.set_event_loop(self._loop)
        self._started.set()
        self._loop.run_forever()

    # ------------------------------------------------------------------
    # 初始化（在后台事件循环中完成）
    # ------------------------------------------------------------------

    async def _init_client_and_agent(self):
        server_script = get_abs_path("agent/mcp/server.py")

        self._client = MultiServerMCPClient(
            {
                "sweepmind": {
                    "command": sys.executable,
                    "args": [server_script],
                    "transport": "stdio",
                }
            }
        )

        tools = await self._client.get_tools()
        middleware_ref = self.middleware

        def dynamic_prompt(state):
            system_prompt = middleware_ref.get_system_prompt()
            return [SystemMessage(content=system_prompt)] + state["messages"]

        self._agent = create_react_agent(
            model=chat_model,
            tools=tools,
            prompt=dynamic_prompt,
        )

    def _ensure_initialized(self):
        if self._agent is not None:
            return
        future = asyncio.run_coroutine_threadsafe(self._init_client_and_agent(), self._loop)
        future.result()  # 阻塞等待初始化完成

    # ------------------------------------------------------------------
    # 流式执行
    # ------------------------------------------------------------------

    async def _stream_to_queue(self, query: str, out: queue.Queue):
        """在后台事件循环中运行 Agent 流，将结果逐条放入线程安全队列。"""
        input_dict = {"messages": [HumanMessage(content=query)]}

        try:
            async for chunk in self._agent.astream(input_dict, stream_mode="values"):
                latest_message = chunk["messages"][-1]

                if hasattr(latest_message, "tool_calls") and latest_message.tool_calls:
                    for tc in latest_message.tool_calls:
                        self._pending_tool_args[tc["name"]] = tc.get("args", {})

                if isinstance(latest_message, ToolMessage):
                    tool_name = latest_message.name
                    tool_args = self._pending_tool_args.pop(tool_name, {})
                    try:
                        self.middleware.on_tool_call(tool_name, tool_args, latest_message.content)
                    except Exception as e:
                        self.middleware.on_tool_error(tool_name, e)

                if latest_message.content:
                    text = latest_message.content
                    if isinstance(text, list):
                        text = "".join(
                            block.get("text", "") if isinstance(block, dict) else str(block)
                            for block in text
                        )
                    if text:
                        out.put(text.strip())
        except Exception as e:
            out.put(e)
        finally:
            out.put(None)  # 结束信号

    def execute_stream(self, query: str):
        """同步生成器，与原 ReactAgent.execute_stream 签名一致。"""
        self._ensure_initialized()

        self.middleware.on_before_model(
            message_count=1,
            last_message_type="HumanMessage",
            last_message_content=query,
        )

        out: queue.Queue = queue.Queue()
        asyncio.run_coroutine_threadsafe(self._stream_to_queue(query, out), self._loop)

        # 主线程同步消费队列
        while True:
            item = out.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item + "\n"

    # ------------------------------------------------------------------
    # 清理
    # ------------------------------------------------------------------

    def cleanup(self):
        self._client = None
        self._agent = None
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._bg_thread.join(timeout=5)
