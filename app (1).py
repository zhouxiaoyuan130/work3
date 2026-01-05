"""
平台人格群聊系统 - Streamlit 版本
部署到 Streamlit Cloud 获取在线链接
"""

import streamlit as st
import json
import random
import time
import base64
import os
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import httpx

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="平台人格群聊",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 配置 ====================
BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"

def load_config(name: str) -> dict:
    """加载配置文件"""
    config_path = CONFIG_DIR / f"{name}.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# 加载配置
PLATFORMS = load_config("platforms")
TOPICS = load_config("topics")
SECRETS = load_config("secrets")

# 内置话题（后备方案）
DEFAULT_TOPICS = [
    {"category": "社会热点", "title": "年轻人为什么不想结婚了？"},
    {"category": "社会热点", "title": "35岁危机是贩卖焦虑还是真实存在？"},
    {"category": "社会热点", "title": "躺平和内卷，你选哪个？"},
    {"category": "互联网", "title": "短视频是不是在毁掉年轻人？"},
    {"category": "互联网", "title": "互联网大厂还值得去吗？"},
    {"category": "互联网", "title": "AI会取代人类的工作吗？"},
    {"category": "生活", "title": "租房还是买房？"},
    {"category": "生活", "title": "一线城市还是回老家？"},
    {"category": "生活", "title": "存钱重要还是享受当下重要？"},
    {"category": "情感", "title": "门当户对重要吗？"},
    {"category": "情感", "title": "异地恋能长久吗？"},
    {"category": "情感", "title": "该不该查伴侣手机？"},
    {"category": "娱乐", "title": "为什么国产剧越来越难看？"},
    {"category": "娱乐", "title": "饭圈文化是好是坏？"},
    {"category": "职场", "title": "加班文化合理吗？"},
    {"category": "职场", "title": "领导PUA怎么破？"},
    {"category": "教育", "title": "学历还重要吗？"},
    {"category": "教育", "title": "鸡娃还是放养？"},
]

# 平台信息
PLATFORM_INFO = {
    "douyin": {"name": "抖音", "icon": "🎵", "color": "#000000", "voice": "zh-CN-XiaoyiNeural"},
    "zhihu": {"name": "知乎", "icon": "📚", "color": "#0066FF", "voice": "zh-CN-YunxiNeural"},
    "xiaohongshu": {"name": "小红书", "icon": "📕", "color": "#FF2442", "voice": "zh-CN-XiaoxiaoNeural"},
    "weibo": {"name": "微博", "icon": "🔥", "color": "#FF8200", "voice": "zh-CN-YunyangNeural"},
    "x": {"name": "X/推特", "icon": "𝕏", "color": "#000000", "voice": "en-US-JennyNeural"},
    "tieba": {"name": "贴吧", "icon": "🏛️", "color": "#4A90E2", "voice": "zh-CN-YunjianNeural"},
}

# ==================== TTS 服务 ====================

def generate_edge_tts_sync(text: str, voice: str) -> bytes:
    """使用免费的 Edge TTS 生成语音（同步版本）"""
    try:
        # 使用命令行方式调用 edge-tts
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            temp_path = f.name
        
        cmd = ['edge-tts', '--voice', voice, '--text', text, '--write-media', temp_path]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(temp_path):
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            os.unlink(temp_path)
            return audio_data
    except Exception as e:
        pass  # 语音生成失败时静默处理
    
    return None

def generate_fish_audio_sync(text: str, api_key: str, voice_id: str) -> Optional[bytes]:
    """使用 Fish Audio 生成用户语音（同步版本）"""
    if not api_key or not voice_id:
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "reference_id": voice_id,
            "format": "mp3",
            "mp3_bitrate": 128,
        }
        
        response = httpx.post(
            "https://api.fish.audio/v1/tts",
            headers=headers,
            json=payload,
            timeout=30.0
        )
        
        if response.status_code == 200:
            return response.content
    except Exception:
        pass  # 静默处理错误
    
    return None

def get_audio_html(audio_data: bytes, autoplay: bool = True) -> str:
    """生成自动播放的音频HTML"""
    b64 = base64.b64encode(audio_data).decode()
    autoplay_attr = "autoplay" if autoplay else ""
    return f'<audio {autoplay_attr} controls style="height:30px;width:100%;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'

# ==================== LLM API ====================

def call_deepseek_sync(messages: List[Dict], api_key: str) -> str:
    """调用 DeepSeek API（同步版本）"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 500,
    }
    
    try:
        response = httpx.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30.0
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[API错误: {e}]"

def call_zhipu_sync(messages: List[Dict], api_key: str) -> str:
    """调用智谱 GLM-4 API（同步版本）"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "glm-4-flash",
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 500,
    }
    
    try:
        response = httpx.post(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers=headers,
            json=data,
            timeout=30.0
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[API错误: {e}]"

def mock_response(platform_id: str) -> str:
    """模拟回复（无API时使用）"""
    responses = {
        "douyin": ["家人们！这话题太绝了！", "哈哈哈不是\n这也太真实了", "DNA动了必须说两句"],
        "zhihu": ["谢邀。这个问题其实涉及到几个层面...", "先问是不是，再问为什么。", "作为相关领域从业者，我认为..."],
        "xiaohongshu": ["姐妹们！！这个话题我必须说！！✨", "天呐！绝绝子！！💕", "这个真的太有共鸣了呜呜呜～"],
        "weibo": ["这话题热搜预定 #今日讨论#", "啊啊啊！！太敢说了！！", "震惊！这波我站..."],
        "x": ["This is actually quite nuanced...", "Interesting take. However...", "From a global perspective..."],
        "tieba": ["乐，经典话题", "典中典了属于是", "绷不住了，太真实"],
    }
    return random.choice(responses.get(platform_id, ["..."]))

# ==================== 自定义CSS ====================

def load_custom_css():
    st.markdown("""
    <style>
    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 主容器 */
    .main .block-container {
        padding: 1rem 2rem;
        max-width: 1200px;
    }
    
    /* 聊天消息容器 */
    .chat-container {
        background: #0a0a0a;
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        max-height: 500px;
        overflow-y: auto;
    }
    
    /* 消息样式 */
    .message {
        display: flex;
        gap: 12px;
        margin: 16px 0;
        animation: fadeIn 0.3s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .message.user {
        flex-direction: row-reverse;
    }
    
    .message-avatar {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
    }
    
    .message-content {
        max-width: 70%;
    }
    
    .message-header {
        font-size: 12px;
        color: #888;
        margin-bottom: 4px;
        padding: 0 4px;
    }
    
    .message.user .message-header {
        text-align: right;
    }
    
    .message-bubble {
        padding: 12px 16px;
        border-radius: 18px;
        font-size: 14px;
        line-height: 1.5;
    }
    
    .message.platform .message-bubble {
        background: #1e1e1e;
        color: #fff;
        border-bottom-left-radius: 4px;
    }
    
    .message.user .message-bubble {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: white;
        border-bottom-right-radius: 4px;
    }
    
    .message.system .message-bubble {
        background: transparent;
        color: #666;
        text-align: center;
        font-size: 13px;
    }
    
    /* 破防特效 */
    .message.breakpoint .message-bubble {
        background: linear-gradient(135deg, #dc2626, #991b1b);
        animation: shake 0.5s ease;
    }
    
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
    
    .breakpoint-tag {
        display: inline-block;
        background: #ef4444;
        color: white;
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 10px;
        margin-bottom: 8px;
    }
    
    /* 情绪条 */
    .emotion-bar {
        background: #1a1a1a;
        border-radius: 12px;
        padding: 16px;
        margin: 10px 0;
    }
    
    .emotion-item {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 8px 0;
    }
    
    .emotion-track {
        flex: 1;
        height: 8px;
        background: #333;
        border-radius: 4px;
        overflow: hidden;
    }
    
    .emotion-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
    }
    
    .emotion-fill.high { background: linear-gradient(90deg, #22c55e, #4ade80); }
    .emotion-fill.medium { background: linear-gradient(90deg, #eab308, #fbbf24); }
    .emotion-fill.low { background: linear-gradient(90deg, #ef4444, #f87171); }
    
    /* 平台选择卡片 */
    .platform-card {
        background: #1a1a1a;
        border: 2px solid transparent;
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .platform-card:hover {
        background: #252525;
        transform: translateY(-2px);
    }
    
    .platform-card.selected {
        border-color: #3b82f6;
        background: rgba(59, 130, 246, 0.1);
    }
    
    /* 话题卡片 */
    .topic-card {
        background: #1a1a1a;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 8px 0;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .topic-card:hover {
        background: #252525;
    }
    
    /* 私信弹窗 */
    .private-msg {
        background: linear-gradient(135deg, #1e1e1e, #2a2a2a);
        border: 1px solid #3b82f6;
        border-radius: 16px;
        padding: 20px;
        margin: 16px 0;
    }
    
    .private-msg-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;
    }
    
    /* 总结卡片 */
    .summary-card {
        background: linear-gradient(135deg, #1e1e1e, #2a2a2a);
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
    }
    
    .soul-type {
        text-align: center;
        padding: 24px;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        border-radius: 12px;
        margin-bottom: 20px;
    }
    
    .soul-type h2 {
        margin: 0 0 8px 0;
        color: white;
    }
    
    .soul-type p {
        margin: 0;
        color: rgba(255,255,255,0.9);
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== 会话状态初始化 ====================

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
    if "turn_count" not in st.session_state:
        st.session_state.turn_count = 0
    if "pending_audio" not in st.session_state:
        st.session_state.pending_audio = None
    if "private_msg" not in st.session_state:
        st.session_state.private_msg = None

# ==================== 核心功能 ====================

def get_random_topics(count: int = 6) -> List[Dict]:
    """获取随机话题"""
    all_topics = []
    
    # 从配置文件加载
    for category, topics in TOPICS.items():
        if isinstance(topics, list):
            for topic in topics:
                if isinstance(topic, dict):
                    all_topics.append({
                        "category": category,
                        "title": topic.get("title", topic.get("topic", str(topic))),
                    })
    
    # 如果配置文件没有话题，使用内置话题
    if not all_topics:
        all_topics = DEFAULT_TOPICS.copy()
    
    return random.sample(all_topics, min(count, len(all_topics)))

def build_system_prompt(platform_id: str, topic: str, other_platform: str) -> str:
    """构建系统提示词"""
    platform = PLATFORMS.get(platform_id, {})
    name = PLATFORM_INFO.get(platform_id, {}).get("name", platform_id)
    other_name = PLATFORM_INFO.get(other_platform, {}).get("name", other_platform)
    
    traits = platform.get("core_traits", [])
    style = platform.get("speaking_style", {})
    
    return f"""你是{name}的拟人化形象，正在和{other_name}讨论话题：{topic}

你的性格特点：{', '.join(traits[:5]) if traits else '活泼有趣'}
说话风格：{style.get('tone', '活泼')}
口头禅：{', '.join(style.get('catchphrases', [])[:3]) if style.get('catchphrases') else '无'}

规则：
1. 保持角色一致性，用{name}的典型说话方式
2. 回复简短有力，不超过100字
3. 可以和{other_name}互动、争论、调侃
4. 适当使用平台特色表达方式

注意：你是{name}，不是AI助手。直接以{name}的身份回复。"""

def generate_ai_response(platform_id: str, topic: str, other_platform: str, history: List[Dict]) -> str:
    """生成AI回复（同步版本）"""
    system_prompt = build_system_prompt(platform_id, topic, other_platform)
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-10:]:  # 只用最近10条
        if msg.get("role") == "user":
            messages.append({"role": "user", "content": msg.get("content", "")})
        elif msg.get("platform_id") == platform_id:
            messages.append({"role": "assistant", "content": msg.get("content", "")})
        elif msg.get("platform_id") and msg.get("platform_id") in PLATFORM_INFO:
            pid = msg.get("platform_id")
            messages.append({"role": "user", "content": f"[{PLATFORM_INFO[pid]['name']}]: {msg.get('content', '')}"})
    
    # 尝试调用API
    deepseek_key = st.session_state.get("deepseek_key", "")
    zhipu_key = st.session_state.get("zhipu_key", "")
    
    if deepseek_key:
        return call_deepseek_sync(messages, deepseek_key)
    elif zhipu_key:
        return call_zhipu_sync(messages, zhipu_key)
    else:
        return mock_response(platform_id)

def check_breakpoint(platform_id: str, user_message: str) -> bool:
    """检查是否触发破防"""
    secrets = SECRETS.get(platform_id, {})
    triggers = secrets.get("breakpoint_triggers", [])
    
    for trigger in triggers:
        if trigger.lower() in user_message.lower():
            return True
    
    # 情绪值过低也触发
    emotion = st.session_state.emotions.get(platform_id, 70)
    return emotion < 15

def get_breakpoint_response(platform_id: str) -> str:
    """获取破防回复"""
    secrets = SECRETS.get(platform_id, {})
    responses = secrets.get("breakpoint_responses", ["...我..."])
    return random.choice(responses)

def update_emotion(platform_id: str, delta: int):
    """更新情绪值"""
    current = st.session_state.emotions.get(platform_id, 70)
    new_value = max(0, min(100, current + delta))
    st.session_state.emotions[platform_id] = new_value

# ==================== UI 渲染 ====================

def render_message(msg: Dict, autoplay_audio: bool = False):
    """渲染单条消息"""
    role = msg.get("role", "system")
    content = msg.get("content", "")
    platform_id = msg.get("platform_id")
    is_breakpoint = msg.get("is_breakpoint", False)
    audio_data = msg.get("audio")
    
    if role == "system":
        st.markdown(f"""
        <div class="message system">
            <div class="message-content" style="width:100%;text-align:center;">
                <div class="message-bubble">{content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    if role == "user":
        st.markdown(f"""
        <div class="message user">
            <div class="message-avatar" style="background:#3b82f6;color:white;">👤</div>
            <div class="message-content">
                <div class="message-header">你</div>
                <div class="message-bubble">{content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        info = PLATFORM_INFO.get(platform_id, {"name": "平台", "icon": "💬", "color": "#666666"})
        breakpoint_tag = '<span class="breakpoint-tag">💔 破防</span>' if is_breakpoint else ''
        breakpoint_class = ' breakpoint' if is_breakpoint else ''
        
        color = info.get('color', '#666666')
        icon = info.get('icon', '💬')
        name = info.get('name', '平台')
        
        st.markdown(f"""
        <div class="message platform{breakpoint_class}">
            <div class="message-avatar" style="background:{color};color:white;">{icon}</div>
            <div class="message-content">
                <div class="message-header">{name}</div>
                {breakpoint_tag}
                <div class="message-bubble">{content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 音频播放
    if audio_data:
        audio_html = get_audio_html(audio_data, autoplay=autoplay_audio)
        st.markdown(audio_html, unsafe_allow_html=True)

def render_emotion_bar():
    """渲染情绪条"""
    if not st.session_state.selected_platforms:
        return
    
    st.markdown('<div class="emotion-bar">', unsafe_allow_html=True)
    
    cols = st.columns(len(st.session_state.selected_platforms))
    for i, pid in enumerate(st.session_state.selected_platforms):
        info = PLATFORM_INFO.get(pid, {"name": "平台", "icon": "💬", "color": "#666666"})
        value = st.session_state.emotions.get(pid, 70)
        level = "high" if value > 60 else "medium" if value > 30 else "low"
        emoji = "😊" if value > 60 else "😐" if value > 30 else "😢"
        
        icon = info.get('icon', '💬')
        
        with cols[i]:
            st.markdown(f"""
            <div class="emotion-item">
                <span style="font-size:20px;">{icon}</span>
                <div class="emotion-track">
                    <div class="emotion-fill {level}" style="width:{value}%"></div>
                </div>
                <span>{emoji} {value}%</span>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_summary():
    """渲染对话总结"""
    st.markdown('<div class="summary-card">', unsafe_allow_html=True)
    
    # 灵魂类型
    soul_types = [
        {"name": "理性派学者", "desc": "你倾向于深思熟虑，喜欢有条理的分析"},
        {"name": "娱乐至上主义者", "desc": "你追求快乐，喜欢轻松有趣的内容"},
        {"name": "情感共鸣者", "desc": "你重视情感连接，容易与他人产生共鸣"},
        {"name": "吃瓜群众", "desc": "你热爱围观，对热点话题充满好奇"},
        {"name": "国际视野者", "desc": "你关注全球动态，思维开放"},
        {"name": "老互联网人", "desc": "你经历过互联网的黄金时代，见多识广"},
    ]
    soul = random.choice(soul_types)
    
    st.markdown(f"""
    <div class="soul-type">
        <h2>🔮 {soul['name']}</h2>
        <p>{soul['desc']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 平台成分
    st.markdown("### 📊 平台成分")
    for pid in st.session_state.selected_platforms:
        info = PLATFORM_INFO.get(pid, {"name": "平台", "icon": "💬", "color": "#666666"})
        score = random.randint(20, 80)
        icon = info.get('icon', '💬')
        name = info.get('name', '平台')
        st.progress(score / 100, text=f"{icon} {name}: {score}%")
    
    # 毒舌点评
    roasts = [
        "你的发言风格很有特色，就是有时候太跳脱了",
        "能看出你是个有想法的人，虽然想法有时候很离谱",
        "你的互联网冲浪技术还需要提高，多看看评论区",
        "典型的键盘侠思维，但至少你愿意发言",
    ]
    st.markdown(f"""
    ### 💬 毒舌点评
    > {random.choice(roasts)}
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==================== 主应用 ====================

def main():
    init_session_state()
    load_custom_css()
    
    # ===== 侧边栏 =====
    with st.sidebar:
        st.title("🎭 平台人格群聊")
        st.caption("让AI平台吵起来，看谁先破防！")
        
        st.divider()
        
        # API 配置
        with st.expander("⚙️ API 配置", expanded=False):
            # 安全获取 secrets
            def get_secret(key, default=""):
                try:
                    return st.secrets[key]
                except:
                    return default
            
            default_deepseek = get_secret("DEEPSEEK_API_KEY", "")
            default_zhipu = get_secret("ZHIPU_API_KEY", "")
            default_fish_key = get_secret("FISH_AUDIO_API_KEY", "")
            default_fish_voice = get_secret("FISH_AUDIO_VOICE_ID", "")
            
            st.session_state.deepseek_key = st.text_input(
                "DeepSeek API Key", 
                value=default_deepseek,
                type="password",
                help="https://platform.deepseek.com 获取"
            )
            st.session_state.zhipu_key = st.text_input(
                "智谱 API Key", 
                value=default_zhipu,
                type="password",
                help="https://open.bigmodel.cn 获取"
            )
            st.divider()
            st.session_state.fish_key = st.text_input(
                "Fish Audio API Key",
                value=default_fish_key,
                type="password",
                help="用于你发言的语音"
            )
            st.session_state.fish_voice = st.text_input(
                "Fish Audio 音色ID",
                value=default_fish_voice,
                help="你的音色ID"
            )
        
        st.divider()
        
        # 平台选择
        st.subheader("选择两个平台")
        
        cols = st.columns(3)
        for i, (pid, info) in enumerate(PLATFORM_INFO.items()):
            with cols[i % 3]:
                selected = pid in st.session_state.selected_platforms
                if st.button(
                    f"{info['icon']}\n{info['name']}", 
                    key=f"platform_{pid}",
                    use_container_width=True,
                    type="primary" if selected else "secondary"
                ):
                    if selected:
                        st.session_state.selected_platforms.remove(pid)
                    elif len(st.session_state.selected_platforms) < 2:
                        st.session_state.selected_platforms.append(pid)
                        st.session_state.emotions[pid] = 70
                    st.rerun()
        
        if st.session_state.selected_platforms:
            names = [PLATFORM_INFO.get(p, {}).get("name", p) for p in st.session_state.selected_platforms]
            st.success(f"已选: {' vs '.join(names)}")
        
        st.divider()
        
        # 话题选择
        st.subheader("选择话题")
        
        # 确保总是有话题
        if "topics" not in st.session_state or not st.session_state.topics:
            st.session_state.topics = get_random_topics()
        
        # 如果还是空的（极端情况），使用硬编码话题
        if not st.session_state.topics:
            st.session_state.topics = [
                {"category": "热点", "title": "年轻人为什么不想结婚了？"},
                {"category": "热点", "title": "35岁危机是真的吗？"},
                {"category": "热点", "title": "躺平还是内卷？"},
                {"category": "互联网", "title": "短视频在毁掉年轻人吗？"},
                {"category": "生活", "title": "租房还是买房？"},
                {"category": "情感", "title": "门当户对重要吗？"},
            ]
        
        for topic in st.session_state.topics:
            if st.button(
                f"🔥 {topic['title']}", 
                key=f"topic_{topic['title']}",
                use_container_width=True,
                type="primary" if st.session_state.current_topic == topic['title'] else "secondary"
            ):
                st.session_state.current_topic = topic['title']
                st.rerun()
        
        if st.button("🔄 换一批", use_container_width=True):
            st.session_state.topics = get_random_topics()
            st.rerun()
        
        st.divider()
        
        # 开始/结束按钮
        if not st.session_state.is_chatting:
            can_start = len(st.session_state.selected_platforms) == 2 and st.session_state.current_topic
            if st.button(
                "🚀 开始群聊", 
                use_container_width=True, 
                disabled=not can_start,
                type="primary"
            ):
                st.session_state.is_chatting = True
                st.session_state.messages = []
                st.session_state.turn_count = 0
                
                # 添加开场消息
                p1, p2 = st.session_state.selected_platforms
                p1_info = PLATFORM_INFO.get(p1, {"icon": "💬", "name": "平台1"})
                p2_info = PLATFORM_INFO.get(p2, {"icon": "💬", "name": "平台2"})
                st.session_state.messages.append({
                    "role": "system",
                    "content": f"📢 群聊开始！话题：{st.session_state.current_topic}"
                })
                st.session_state.messages.append({
                    "role": "system",
                    "content": f"{p1_info.get('icon', '💬')} {p1_info.get('name', '平台1')} 和 {p2_info.get('icon', '💬')} {p2_info.get('name', '平台2')} 加入了群聊"
                })
                st.rerun()
        else:
            if st.button("🛑 结束对话", use_container_width=True, type="secondary"):
                st.session_state.is_chatting = False
                st.session_state.show_summary = True
                st.rerun()
    
    # ===== 主聊天区域 =====
    if not st.session_state.is_chatting:
        if st.session_state.get("show_summary"):
            render_summary()
            if st.button("🔄 重新开始", type="primary"):
                st.session_state.show_summary = False
                st.session_state.selected_platforms = []
                st.session_state.current_topic = None
                st.rerun()
        else:
            st.markdown("""
            <div style="text-align:center;padding:100px 20px;color:#666;">
                <div style="font-size:64px;margin-bottom:20px;">💬</div>
                <h2 style="color:#888;">选择平台和话题</h2>
                <p>让AI平台们吵起来，看看谁会先破防！</p>
            </div>
            """, unsafe_allow_html=True)
        return
    
    # 聊天头部
    p1, p2 = st.session_state.selected_platforms
    p1_info = PLATFORM_INFO.get(p1, {"icon": "💬", "name": "平台1"})
    p2_info = PLATFORM_INFO.get(p2, {"icon": "💬", "name": "平台2"})
    st.markdown(f"""
    ### {p1_info.get('icon', '💬')} {p1_info.get('name', '平台1')} vs {p2_info.get('icon', '💬')} {p2_info.get('name', '平台2')}
    **话题**: {st.session_state.current_topic}
    """)
    
    # 情绪条
    render_emotion_bar()
    
    st.divider()
    
    # 消息列表
    chat_container = st.container()
    with chat_container:
        for i, msg in enumerate(st.session_state.messages):
            # 最后一条消息自动播放
            autoplay = (i == len(st.session_state.messages) - 1) and msg.get("audio")
            render_message(msg, autoplay_audio=autoplay)
    
    # 输入区域
    st.divider()
    
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            "说点什么...", 
            key="user_input",
            label_visibility="collapsed"
        )
    with col2:
        send_clicked = st.button("发送", type="primary", use_container_width=True)
    
    # 处理发送
    if send_clicked and user_input:
        handle_send_message_sync(user_input)
        st.rerun()

def handle_send_message_sync(user_input: str):
    """同步方式处理发送消息"""
    p1, p2 = st.session_state.selected_platforms
    
    # 生成用户语音（Fish Audio）
    user_audio = None
    if st.session_state.get("fish_key") and st.session_state.get("fish_voice"):
        user_audio = generate_fish_audio_sync(
            user_input,
            st.session_state.fish_key,
            st.session_state.fish_voice
        )
    
    # 添加用户消息
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "audio": user_audio
    })
    
    # 两个平台依次回复
    for pid in [p1, p2]:
        other = p2 if pid == p1 else p1
        
        # 检查破防
        is_breakpoint = check_breakpoint(pid, user_input)
        
        if is_breakpoint:
            response = get_breakpoint_response(pid)
            update_emotion(pid, -30)
        else:
            # 调用 AI 生成回复
            response = generate_ai_response(
                pid, 
                st.session_state.current_topic,
                other,
                st.session_state.messages
            )
            update_emotion(pid, random.randint(-10, 5))
        
        # 生成AI语音（免费 Edge TTS）
        audio_data = None
        voice = PLATFORM_INFO.get(pid, {}).get("voice", "zh-CN-XiaoyiNeural")
        audio_data = generate_edge_tts_sync(response, voice)
        
        st.session_state.messages.append({
            "role": "platform",
            "platform_id": pid,
            "content": response,
            "is_breakpoint": is_breakpoint,
            "audio": audio_data
        })
    
    st.session_state.turn_count += 1

# ==================== 入口 ====================

if __name__ == "__main__":
    main()
