import json

from utils.logger_handler import logger
from utils.prompt_loader import load_report_prompts, load_system_prompts


class MCPMiddlewareManager:
    """客户端侧的中间件管理器，替代原有 agent/tools/middleware.py 中的三个钩子。"""

    def __init__(self):
        self.report_mode: bool = False

    # ---- 工具调用监控（替代 @wrap_tool_call monitor_tool）----

    def on_tool_call(self, tool_name: str, tool_args: dict, tool_result: str) -> str:
        logger.info(f"[tool monitor]执行工具：{tool_name}")
        logger.info(f"[tool monitor]传入参数：{tool_args}")
        logger.info(f"[tool monitor]工具{tool_name}调用成功")

        if tool_name == "fill_context_for_report":
            try:
                parsed = json.loads(tool_result)
                if parsed.get("__mcp_signal__") == "report_mode":
                    self.report_mode = True
                    logger.info("[tool monitor]检测到报告模式信号，已切换context")
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass

        return tool_result

    def on_tool_error(self, tool_name: str, error: Exception):
        logger.error(f"工具{tool_name}调用失败，原因：{str(error)}")

    # ---- 模型调用前日志（替代 @before_model log_before_model）----

    def on_before_model(self, message_count: int, last_message_type: str, last_message_content: str):
        logger.info(f"[log_before_model]即将调用模型，带有{message_count}条消息。")
        logger.debug(f"[log_before_model]{last_message_type} | {last_message_content}")

    # ---- 动态提示词切换（替代 @dynamic_prompt report_prompt_switch）----

    def get_system_prompt(self) -> str:
        if self.report_mode:
            return load_report_prompts()
        return load_system_prompts()

    def reset(self):
        self.report_mode = False
