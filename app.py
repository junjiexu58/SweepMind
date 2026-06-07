import time

import streamlit as st
from utils.config_handler import agent_conf

if agent_conf.get("use_mcp", False):
    from agent.mcp_react_agent import MCPReactAgent as AgentClass
else:
    from agent.react_agent import ReactAgent as AgentClass

# 页面配置 (可选，设置页面标题和较宽的布局)
st.set_page_config(page_title="SweepMind - 扫地机器人智能客服", layout="wide")

# ================= 新增：侧边栏使用说明 =================
with st.sidebar:
    st.markdown("### 💬 使用方式")
    st.markdown("你可以在网页聊天界面进行以下操作：")

    st.markdown("#### 📦 产品咨询")
    st.caption("直接提问关于扫地机器人的使用、维护、故障排除等问题，Agent 会优先从知识库中检索相关资料进行回答：")
    st.info("""
    - **用户**：扫地机器人的滤网多久需要更换一次？
    - **用户**：扫拖一体机器人和扫地机器人有什么区别？
    - **用户**：扫地机器人吸力变弱了怎么办？
    """)

    st.markdown("#### 🌤️ 天气查询")
    st.caption("Agent 可调用和风天气 API 获取实时信息：")
    st.info("""
    - **用户**：北京今天的天气怎么样？
    """)

    st.markdown("#### 📊 使用报告生成")
    st.caption("Agent 会自动检测报告生成意图，切换到报告提示词，并调用外部数据生成 Markdown 格式的使用情况报告：")
    st.info("""
    - **用户**：帮我生成我的使用报告
    - **用户**：给我一份扫地机器人的使用分析和保养建议
    """)
# ========================================================

# 标题
st.title("SweepMind 扫地机器人智能客服 🤖")
st.caption("你好!我是您的专属客服，很高兴为您服务！")
st.divider()

if "agent" not in st.session_state:
    st.session_state["agent"] = AgentClass()

if "message" not in st.session_state:
    st.session_state["message"] = []

for message in st.session_state["message"]:
    st.chat_message(message["role"]).write(message["content"])

# 用户输入提示词
prompt = st.chat_input()

if prompt:
    st.chat_message("user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    response_messages = []
    with st.spinner("智能客服思考中..."):
        res_stream = st.session_state["agent"].execute_stream(prompt)

        def capture(generator, cache_list):

            for chunk in generator:
                cache_list.append(chunk)

                for char in chunk:
                    time.sleep(0.01)
                    yield char

        st.chat_message("assistant").write_stream(capture(res_stream, response_messages))
        st.session_state["message"].append({"role": "assistant", "content": response_messages[-1]})
        st.rerun()

