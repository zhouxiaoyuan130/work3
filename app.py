"""
平台人格群聊系统 - Streamlit 精简版
"""

import streamlit as st
import json
import random
import time
from pathlib import Path
from typing import Optional, Dict, List

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="平台人格群聊",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 平台配置（内置） ====================
PLATFORM_INFO = {
    "douyin": {"name": "抖音", "icon": "🎵", "color": "#000000"},
    "zhihu": {"name": "知乎", "icon": "📚", "color": "#0066FF"},
    "xiaohongshu": {"name": "小红书", "icon": "📕", "color": "#FF2442"},
    "weibo": {"name": "微博", "icon": "🔥", "color": "#FF8200"},
    "x": {"name": "X/推特", "icon": "𝕏", "color": "#000000"},
    "tieba": {"name": "贴吧", "icon": "🏛️", "color": "#4A90E2"},
}

# 内置话题
DEFAULT_TOPICS = [
    {"category": "社会热点", "title": "年轻人为什么不想结婚了？"},
    {"category": "社会热点", "title": "35岁危机是贩卖焦虑还是真实存在？"},
    {"category": "社会热点", "title": "躺平和内卷，你选哪个？"},
    {"category": "互联网", "title": "短视频是不是在毁掉年轻人？"},
    {"category": "互联网", "title": "AI会取代人类的工作吗？"},
    {"category": "生活", "title": "租房还是买房？"},
    {"category": "生活", "title": "一线城市还是回老家？"},
    {"category": "情感", "title": "门当户对重要吗？"},
    {"category": "职场", "title": "加班文化合理吗？"},
]

# 模拟回复（每个平台的风格）
MOCK_RESPONSES = {
    "douyin": [
        "家人们谁懂啊！这话题太真实了！",
        "不是\n我就说一句\n这事儿真的离谱",
        "笑死我了哈哈哈哈\n@知乎 你来评评理",
        "DNA动了！必须说两句！",
        "救命 这也太real了吧",
        "我的评价是：不如跳舞💃",
    ],
    "zhihu": [
        "谢邀。这个问题其实涉及到几个层面，让我来系统分析一下...",
        "先问是不是，再问为什么。从数据来看...",
        "作为一个在相关领域工作多年的人，我认为这个问题需要从本质上理解。",
        "这个问题下的回答质量堪忧。容我来写一篇长文。",
        "利益相关：我就是干这行的。简单说几点...",
        "看了其他平台的发言，我只能说：果然是信息茧房的受害者。",
    ],
    "xiaohongshu": [
        "姐妹们！！这个话题我真的必须说！！✨",
        "天呐绝绝子！！太有共鸣了叭💕",
        "救命这也太真实了吧😭😭手动艾特闺蜜",
        "啊啊啊啊！码住！这条我要收藏！📌",
        "宝子们听我说！这事儿真的很重要！💗",
        "呜呜呜被戳中了...姐妹抱抱🤗",
    ],
    "weibo": [
        "这话题 热搜预定了 #今日讨论#",
        "震惊！没想到评论区这么热闹！",
        "啊啊啊啊太敢说了！！转发！",
        "吃瓜吃到自己头上了 [吃瓜]",
        "看看这评论区 人间真实 [笑cry]",
        "[并不简单] 这波我站... 算了不说了怕被喷",
    ],
    "x": [
        "Interesting take. From my perspective...",
        "This is actually quite nuanced. Let me explain.",
        "Based. This is exactly what I've been saying.",
        "The global perspective on this is worth considering.",
        "Hot take: most people don't understand this issue at all.",
        "Thread incoming 🧵 1/",
    ],
    "tieba": [
        "乐，经典话题又来了",
        "典中典了属于是",
        "绷不住了，太真实",
        "这下支持了",
        "笑嘻了，老哥们来评评理",
        "蚌埠住了，什么离谱发言",
    ],
}

# ==================== 会话状态 ====================
def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_platforms" not in st.session_state:
        st.session_state.selected_platforms = []
    if "current_topic" not in st.session_state:
        st.session_state.current_topic = None
    if "emotions" not in st.session_state:
        st.session_state.emotions = {}
    if "is_chatting" not in st.session_state:
        st.session_state.is_chatting = False
    if "topics" not in st.session_state:
        st.session_state.topics = random.sample(DEFAULT_TOPICS, 6)

# ==================== API 调用 ====================
def call_llm_api(messages: List[Dict], api_key: str, api_type: str) -> Optional[str]:
    """调用 LLM API"""
    try:
        import httpx
        
        if api_type == "deepseek":
            url = "https://api.deepseek.com/v1/chat/completions"
            model = "deepseek-chat"
        else:  # zhipu
            url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            model = "glm-4-flash"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 200,
        }
        
        response = httpx.post(url, headers=headers, json=data, timeout=15.0)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        pass  # 静默失败，使用模拟回复
    
    return None

def get_ai_response(platform_id: str, topic: str, history: List[Dict]) -> str:
    """获取AI回复"""
    # 检查是否有API key
    deepseek_key = st.session_state.get("deepseek_key", "")
    zhipu_key = st.session_state.get("zhipu_key", "")
    
    if deepseek_key or zhipu_key:
        # 构建提示
        platform_name = PLATFORM_INFO[platform_id]["name"]
        system_prompt = f"""你是{platform_name}的拟人化形象。
话题：{topic}
规则：
1. 用{platform_name}用户的典型说话方式回复
2. 回复简短有力，不超过50字
3. 可以调侃其他平台
4. 直接回复，不要说"作为{platform_name}"这样的话"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史消息
        for msg in history[-6:]:
            if msg.get("role") == "user":
                messages.append({"role": "user", "content": msg["content"]})
            elif msg.get("role") == "platform":
                pid = msg.get("platform_id", "")
                pname = PLATFORM_INFO.get(pid, {}).get("name", "平台")
                if pid == platform_id:
                    messages.append({"role": "assistant", "content": msg["content"]})
                else:
                    messages.append({"role": "user", "content": f"[{pname}]: {msg['content']}"})
        
        # 调用API
        api_key = deepseek_key if deepseek_key else zhipu_key
        api_type = "deepseek" if deepseek_key else "zhipu"
        
        result = call_llm_api(messages, api_key, api_type)
        if result:
            return result
    
    # 使用模拟回复
    return random.choice(MOCK_RESPONSES.get(platform_id, ["..."]))

# ==================== 消息处理 ====================
def send_message(user_input: str):
    """处理发送消息"""
    if not user_input.strip():
        return
    
    p1, p2 = st.session_state.selected_platforms
    
    # 1. 添加用户消息
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # 2. 平台1回复
    response1 = get_ai_response(p1, st.session_state.current_topic, st.session_state.messages)
    st.session_state.messages.append({
        "role": "platform",
        "platform_id": p1,
        "content": response1
    })
    
    # 更新情绪
    st.session_state.emotions[p1] = max(0, st.session_state.emotions.get(p1, 70) + random.randint(-10, 5))
    
    # 3. 平台2回复
    response2 = get_ai_response(p2, st.session_state.current_topic, st.session_state.messages)
    st.session_state.messages.append({
        "role": "platform",
        "platform_id": p2,
        "content": response2
    })
    
    # 更新情绪
    st.session_state.emotions[p2] = max(0, st.session_state.emotions.get(p2, 70) + random.randint(-10, 5))

# ==================== UI ====================
def main():
    init_session_state()
    
    # 自定义CSS
    st.markdown("""
    <style>
    .message-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px 0;
        max-width: 70%;
        margin-left: auto;
    }
    .message-platform {
        background: #f0f0f0;
        color: #333;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px 0;
        max-width: 70%;
    }
    .message-system {
        text-align: center;
        color: #888;
        font-size: 0.9em;
        margin: 10px 0;
    }
    .platform-icon {
        display: inline-block;
        width: 30px;
        height: 30px;
        border-radius: 8px;
        text-align: center;
        line-height: 30px;
        margin-right: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ===== 侧边栏 =====
    with st.sidebar:
        st.title("🎭 平台人格群聊")
        
        # API配置
        with st.expander("⚙️ API 配置（可选）"):
            st.session_state.deepseek_key = st.text_input(
                "DeepSeek API Key", 
                type="password",
                help="不填则使用模拟回复"
            )
            st.session_state.zhipu_key = st.text_input(
                "智谱 API Key", 
                type="password",
                help="不填则使用模拟回复"
            )
        
        st.divider()
        
        # 平台选择
        st.subheader("1️⃣ 选择两个平台")
        cols = st.columns(3)
        for i, (pid, info) in enumerate(PLATFORM_INFO.items()):
            with cols[i % 3]:
                selected = pid in st.session_state.selected_platforms
                if st.button(
                    f"{info['icon']}\n{info['name']}", 
                    key=f"p_{pid}",
                    use_container_width=True,
                    type="primary" if selected else "secondary"
                ):
                    if selected:
                        st.session_state.selected_platforms.remove(pid)
                    elif len(st.session_state.selected_platforms) < 2:
                        st.session_state.selected_platforms.append(pid)
                        st.session_state.emotions[pid] = 70
                    st.rerun()
        
        if len(st.session_state.selected_platforms) == 2:
            p1, p2 = st.session_state.selected_platforms
            st.success(f"✅ {PLATFORM_INFO[p1]['name']} vs {PLATFORM_INFO[p2]['name']}")
        
        st.divider()
        
        # 话题选择
        st.subheader("2️⃣ 选择话题")
        for topic in st.session_state.topics:
            selected = st.session_state.current_topic == topic['title']
            if st.button(
                f"{'✅' if selected else '🔥'} {topic['title']}", 
                key=f"t_{topic['title']}",
                use_container_width=True
            ):
                st.session_state.current_topic = topic['title']
                st.rerun()
        
        if st.button("🔄 换一批话题"):
            st.session_state.topics = random.sample(DEFAULT_TOPICS, 6)
            st.rerun()
        
        st.divider()
        
        # 开始按钮
        can_start = len(st.session_state.selected_platforms) == 2 and st.session_state.current_topic
        
        if not st.session_state.is_chatting:
            if st.button("🚀 开始群聊", disabled=not can_start, type="primary", use_container_width=True):
                st.session_state.is_chatting = True
                st.session_state.messages = []
                p1, p2 = st.session_state.selected_platforms
                st.session_state.messages.append({
                    "role": "system",
                    "content": f"📢 话题：{st.session_state.current_topic}"
                })
                st.session_state.messages.append({
                    "role": "system", 
                    "content": f"{PLATFORM_INFO[p1]['icon']} {PLATFORM_INFO[p1]['name']} 和 {PLATFORM_INFO[p2]['icon']} {PLATFORM_INFO[p2]['name']} 加入了群聊"
                })
                st.rerun()
        else:
            if st.button("🛑 结束对话", type="secondary", use_container_width=True):
                st.session_state.is_chatting = False
                st.session_state.messages = []
                st.session_state.selected_platforms = []
                st.session_state.current_topic = None
                st.rerun()
    
    # ===== 主聊天区域 =====
    if not st.session_state.is_chatting:
        st.markdown("""
        <div style="text-align:center;padding:100px 20px;">
            <div style="font-size:80px;margin-bottom:20px;">💬</div>
            <h2>选择平台和话题，开始群聊！</h2>
            <p style="color:#888;">让AI平台们吵起来，看看谁会先破防！</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 显示情绪条
    if st.session_state.selected_platforms:
        cols = st.columns(2)
        for i, pid in enumerate(st.session_state.selected_platforms):
            info = PLATFORM_INFO[pid]
            emotion = st.session_state.emotions.get(pid, 70)
            with cols[i]:
                st.markdown(f"**{info['icon']} {info['name']}**")
                st.progress(emotion / 100, text=f"情绪: {emotion}%")
    
    st.divider()
    
    # 显示消息
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            st.markdown(f"<div class='message-system'>{msg['content']}</div>", unsafe_allow_html=True)
        elif msg["role"] == "user":
            st.markdown(f"<div style='text-align:right'><div class='message-user'>{msg['content']}</div></div>", unsafe_allow_html=True)
        elif msg["role"] == "platform":
            pid = msg.get("platform_id", "")
            info = PLATFORM_INFO.get(pid, {"icon": "💬", "name": "平台", "color": "#666"})
            st.markdown(f"""
            <div>
                <span class='platform-icon' style='background:{info["color"]};color:white;'>{info["icon"]}</span>
                <strong>{info["name"]}</strong>
            </div>
            <div class='message-platform'>{msg["content"]}</div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # 输入框
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input("说点什么...", key="input", label_visibility="collapsed")
    with col2:
        if st.button("发送", type="primary", use_container_width=True):
            if user_input:
                send_message(user_input)
                st.rerun()

if __name__ == "__main__":
    main()
