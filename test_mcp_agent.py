"""MCP Agent 端到端测试脚本。

验证基于 MCP 工具的 Agent 能否正常完成三种典型场景。
用法：python test_mcp_agent.py
"""
from agent.mcp_react_agent import MCPReactAgent


def run_scenario(agent: MCPReactAgent, scenario_name: str, query: str):
    print(f"\n{'='*60}")
    print(f"场景: {scenario_name}")
    print(f"用户: {query}")
    print(f"{'='*60}")

    full_response = ""
    for chunk in agent.execute_stream(query):
        print(chunk, end="", flush=True)
        full_response += chunk

    print()
    return full_response


def main():
    agent = MCPReactAgent()

    # 场景 1: 产品咨询（触发 rag_summarize）
    run_scenario(agent, "产品咨询", "扫地机器人的滤网多久需要更换一次？")

    # 场景 2: 天气查询（触发 get_weather）
    run_scenario(agent, "天气查询", "杭州今天天气怎么样？")

    # 场景 3: 报告生成（触发 fill_context_for_report + 动态 prompt 切换）
    run_scenario(agent, "报告生成", "帮我生成我的使用报告")


if __name__ == "__main__":
    main()
