"""
平台人格群聊系统 - Gradio UI界面
包含：平台选择、话题选择、聊天窗口、私信弹窗、情绪显示、破防/叛变特效、总结页面
"""

import gradio as gr
import json
import random
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio

# 导入核心模块
import sys
sys.path.append(str(Path(__file__).parent.parent))

from core.chat_engine import ChatEngine, MessageType
from core.emotion_system import EmotionSystem, EmotionLevel
from core.private_msg import PrivateMessageSystem, PrivateMessageType
from core.betrayal import BetrayalSystem
from core.soul_test import SoulPurityTest
from audio.fish_audio import FishAudioTTS, VoiceProfile

# ==================== 配置加载 ====================

CONFIG_DIR = Path(__file__).parent.parent / "config"

def load_config(name: str) -> dict:
    """加载配置文件"""
    with open(CONFIG_DIR / f"{name}.json", "r", encoding="utf-8") as f:
        return json.load(f)

# 平台信息
PLATFORMS = load_config("platforms")
RELATIONSHIPS = load_config("relationships")
TOPICS = load_config("topics")
SECRETS = load_config("secrets")

# 平台头像和颜色
PLATFORM_AVATARS = {
    "douyin": "🎵",
    "zhihu": "📚",
    "xiaohongshu": "📕",
    "weibo": "🔥",
    "x": "𝕏",
    "tieba": "🏛️"
}

PLATFORM_COLORS = {
    "douyin": "#000000",
    "zhihu": "#0066FF",
    "xiaohongshu": "#FF2442",
    "weibo": "#FF8200",
    "x": "#1DA1F2",
    "tieba": "#4A90E2"
}

PLATFORM_NAMES = {
    "douyin": "抖音",
    "zhihu": "知乎",
    "xiaohongshu": "小红书",
    "weibo": "微博",
    "x": "X/推特",
    "tieba": "贴吧"
}

# ==================== 会话状态管理 ====================

@dataclass
class SessionState:
    """会话状态"""
    # 基础状态
    selected_platforms: List[str] = field(default_factory=list)
    current_topic: Optional[str] = None
    is_chatting: bool = False
    
    # 核心引擎
    chat_engine: Optional[ChatEngine] = None
    emotion_system: Optional[EmotionSystem] = None
    private_msg_system: Optional[PrivateMessageSystem] = None
    betrayal_system: Optional[BetrayalSystem] = None
    soul_test: Optional[SoulPurityTest] = None
    tts: Optional[FishAudioTTS] = None
    
    # 对话历史
    chat_history: List[Dict] = field(default_factory=list)
    turn_count: int = 0
    
    # 私信状态
    pending_private_msg: Optional[Dict] = None
    
    # 特效状态
    current_effect: Optional[str] = None  # "breakpoint", "betrayal", None
    effect_data: Optional[Dict] = None
    
    # 语音状态
    enable_voice: bool = False
    current_audio: Optional[str] = None

# 全局会话状态
session = SessionState()

# ==================== UI组件样式 ====================

CUSTOM_CSS = """
/* 整体风格 */
.gradio-container {
    font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    min-height: 100vh;
}

/* 主容器 */
.main-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* 标题 */
.title-text {
    text-align: center;
    font-size: 2.5em;
    font-weight: bold;
    color: white;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    margin-bottom: 20px;
}

/* 平台选择卡片 */
.platform-card {
    background: white;
    border-radius: 16px;
    padding: 20px;
    margin: 10px;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.platform-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 15px rgba(0,0,0,0.2);
}

.platform-card.selected {
    border: 3px solid #667eea;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

/* 聊天消息 */
.chat-message {
    padding: 12px 16px;
    margin: 8px 0;
    border-radius: 18px;
    max-width: 80%;
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.chat-message.user {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    margin-left: auto;
    border-bottom-right-radius: 4px;
}

.chat-message.platform {
    background: #f0f0f0;
    color: #333;
    border-bottom-left-radius: 4px;
}

/* 情绪条 */
.emotion-bar {
    height: 8px;
    border-radius: 4px;
    background: #e0e0e0;
    overflow: hidden;
    margin: 5px 0;
}

.emotion-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease, background-color 0.3s ease;
}

.emotion-high { background: linear-gradient(90deg, #4CAF50, #8BC34A); }
.emotion-medium { background: linear-gradient(90deg, #FFC107, #FF9800); }
.emotion-low { background: linear-gradient(90deg, #f44336, #E91E63); }

/* 破防特效 */
.breakpoint-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.8);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    animation: shake 0.5s ease;
}

@keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-10px); }
    75% { transform: translateX(10px); }
}

.breakpoint-content {
    background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
    padding: 40px;
    border-radius: 20px;
    text-align: center;
    color: white;
    max-width: 500px;
}

/* 叛变特效 */
.betrayal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.9);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.betrayal-content {
    background: linear-gradient(135deg, #232526 0%, #414345 100%);
    padding: 40px;
    border-radius: 20px;
    text-align: center;
    color: white;
    max-width: 600px;
    border: 2px solid #ffd700;
    animation: glow 1s ease infinite alternate;
}

@keyframes glow {
    from { box-shadow: 0 0 20px #ffd700; }
    to { box-shadow: 0 0 40px #ffd700; }
}

/* 私信弹窗 */
.private-msg-popup {
    background: white;
    border-radius: 16px;
    padding: 24px;
    max-width: 400px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
}

.private-msg-header {
    display: flex;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #eee;
}

.private-msg-content {
    font-size: 1.1em;
    line-height: 1.6;
    margin-bottom: 20px;
}

.private-msg-options button {
    width: 100%;
    padding: 12px;
    margin: 8px 0;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
}

/* 话题卡片 */
.topic-card {
    background: white;
    border-radius: 12px;
    padding: 16px;
    margin: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    border: 2px solid transparent;
}

.topic-card:hover {
    border-color: #667eea;
    transform: scale(1.02);
}

/* 总结页面 */
.summary-container {
    background: white;
    border-radius: 20px;
    padding: 30px;
    margin: 20px;
}

.soul-result {
    text-align: center;
    padding: 40px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    color: white;
    margin-bottom: 20px;
}

.platform-bar {
    display: flex;
    align-items: center;
    margin: 10px 0;
}

.platform-bar-label {
    width: 80px;
    font-weight: bold;
}

.platform-bar-fill {
    height: 24px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    padding: 0 10px;
    color: white;
    font-size: 0.9em;
    transition: width 1s ease;
}
"""

# ==================== 核心函数 ====================

def initialize_session():
    """初始化会话"""
    global session
    session = SessionState()
    
def select_platform(platform_id: str) -> Tuple[str, str]:
    """选择平台"""
    if platform_id in session.selected_platforms:
        session.selected_platforms.remove(platform_id)
    elif len(session.selected_platforms) < 2:
        session.selected_platforms.append(platform_id)
    
    # 返回选中状态的显示
    status = f"已选择: {', '.join([PLATFORM_NAMES[p] for p in session.selected_platforms])}"
    can_start = len(session.selected_platforms) == 2
    return status, can_start

def get_random_topics(count: int = 3) -> List[Dict]:
    """获取随机话题"""
    all_topics = []
    for category, topics in TOPICS.items():
        if isinstance(topics, list):
            for topic in topics:
                if isinstance(topic, dict):
                    all_topics.append({
                        "category": category,
                        "title": topic.get("title", topic.get("topic", str(topic))),
                        "description": topic.get("description", ""),
                        "conflict_level": topic.get("conflict_level", 0.5)
                    })
                else:
                    all_topics.append({
                        "category": category,
                        "title": str(topic),
                        "description": "",
                        "conflict_level": 0.5
                    })
    
    return random.sample(all_topics, min(count, len(all_topics)))

def start_chat(topic: str) -> str:
    """开始聊天"""
    if len(session.selected_platforms) != 2:
        return "请先选择两个平台！"
    
    session.current_topic = topic
    session.is_chatting = True
    session.turn_count = 0
    session.chat_history = []
    
    # 初始化各系统
    session.emotion_system = EmotionSystem(SECRETS)
    session.private_msg_system = PrivateMessageSystem(PLATFORMS, RELATIONSHIPS, SECRETS)
    session.betrayal_system = BetrayalSystem(PLATFORMS, SECRETS)
    session.soul_test = SoulPurityTest(PLATFORMS)
    
    # 初始化平台情绪
    for platform_id in session.selected_platforms:
        session.emotion_system.initialize_platform(platform_id)
    
    # 生成开场白
    opening = generate_opening_messages()
    
    return opening

def generate_opening_messages() -> List[Dict]:
    """生成开场白"""
    messages = []
    
    p1, p2 = session.selected_platforms
    p1_name = PLATFORM_NAMES[p1]
    p2_name = PLATFORM_NAMES[p2]
    
    # 系统消息
    messages.append({
        "role": "system",
        "content": f"🎭 {p1_name} 和 {p2_name} 进入了群聊\n📢 今日话题: {session.current_topic}"
    })
    
    # 平台开场白（基于人格）
    p1_opening = generate_platform_opening(p1)
    p2_opening = generate_platform_opening(p2)
    
    messages.append({
        "role": "platform",
        "platform_id": p1,
        "content": p1_opening
    })
    
    messages.append({
        "role": "platform",
        "platform_id": p2,
        "content": p2_opening
    })
    
    session.chat_history.extend(messages)
    return messages

def generate_platform_opening(platform_id: str) -> str:
    """生成平台开场白"""
    platform = PLATFORMS.get(platform_id, {})
    personality = platform.get("personality", {})
    speech = platform.get("speech_style", {})
    
    openings = {
        "douyin": [
            "家人们！今天这个话题绝了！",
            "来了来了！这话题DNA动了！",
            "好家伙，这话题有点东西啊"
        ],
        "zhihu": [
            "谢邀，这个问题很有讨论价值。",
            "作为一个长期关注此领域的人，我想从几个角度分析一下。",
            "先问是不是，再问为什么。"
        ],
        "xiaohongshu": [
            "姐妹们！这个话题太有共鸣了！✨",
            "天呐！终于有人聊这个了！💕",
            "绝绝子！这个话题我必须说两句！🔥"
        ],
        "weibo": [
            "这话题热搜预定了吧 #今日话题#",
            "啊啊啊啊终于聊这个了！#吃瓜#",
            "救命！这话题也太敏感了吧 #围观#"
        ],
        "x": [
            "Interesting topic. Let me share my thoughts.",
            "This is something I've been thinking about lately.",
            "Finally, a meaningful discussion. 🧵"
        ],
        "tieba": [
            "乐，又是这种话题",
            "来了，开始表演了",
            "典，经典话题"
        ]
    }
    
    return random.choice(openings.get(platform_id, ["开始讨论吧。"]))

def process_user_message(message: str) -> Tuple[List[Dict], Optional[Dict], Optional[Dict]]:
    """处理用户消息"""
    if not session.is_chatting:
        return [], None, None
    
    session.turn_count += 1
    new_messages = []
    private_msg = None
    effect = None
    
    # 记录用户消息
    user_msg = {
        "role": "user",
        "content": message
    }
    session.chat_history.append(user_msg)
    new_messages.append(user_msg)
    
    # 灵魂测试记录
    if session.soul_test:
        session.soul_test.record_message(message)
    
    # 分析用户消息对各平台的情绪影响
    for platform_id in session.selected_platforms:
        if session.emotion_system:
            events = session.emotion_system.check_triggers(platform_id, message, "user")
            for event in events:
                session.emotion_system.apply_emotion_change(
                    platform_id, 
                    event.get("delta", 0),
                    "user",
                    event.get("reason", "")
                )
    
    # 生成平台回复
    for platform_id in session.selected_platforms:
        # 检查破防
        if session.emotion_system:
            emotion_value = session.emotion_system.get_emotion_value(platform_id)
            if emotion_value < 15:
                # 触发破防
                breakpoint_response = session.emotion_system.get_breakpoint_response(platform_id)
                effect = {
                    "type": "breakpoint",
                    "platform_id": platform_id,
                    "response": breakpoint_response
                }
                new_messages.append({
                    "role": "platform",
                    "platform_id": platform_id,
                    "content": breakpoint_response,
                    "is_breakpoint": True
                })
                session.emotion_system.recover_from_breakpoint(platform_id)
                continue
        
        # 检查叛变
        if session.betrayal_system:
            betrayal_event = session.betrayal_system.check_betrayal_trigger(
                platform_id, 
                session.current_topic,
                session.emotion_system.get_emotion_value(platform_id) if session.emotion_system else 50
            )
            if betrayal_event:
                effect = {
                    "type": "betrayal",
                    "event": betrayal_event
                }
                new_messages.append({
                    "role": "platform",
                    "platform_id": platform_id,
                    "content": betrayal_event.get("statement", "...我可能需要重新思考这个问题。"),
                    "is_betrayal": True
                })
                continue
        
        # 正常回复
        response = generate_platform_response(platform_id, message)
        if isinstance(response, list):
            # 分条消息
            for part in response:
                new_messages.append({
                    "role": "platform",
                    "platform_id": platform_id,
                    "content": part,
                    "is_multi_part": True
                })
        else:
            new_messages.append({
                "role": "platform",
                "platform_id": platform_id,
                "content": response
            })
    
    # 检查私信触发
    if session.private_msg_system and random.random() < 0.3:
        sender = random.choice(session.selected_platforms)
        target = [p for p in session.selected_platforms if p != sender][0]
        private_msg = session.private_msg_system.generate_private_message(sender, target, message)
        if private_msg:
            session.pending_private_msg = private_msg
    
    session.chat_history.extend(new_messages[1:])  # 跳过已添加的用户消息
    
    return new_messages, private_msg, effect

def generate_platform_response(platform_id: str, user_message: str) -> str | List[str]:
    """生成平台回复（模拟LLM响应）"""
    platform = PLATFORMS.get(platform_id, {})
    speech = platform.get("speech_style", {})
    personality = platform.get("personality", {})
    
    # 获取情绪状态
    emotion_value = 50
    if session.emotion_system:
        emotion_value = session.emotion_system.get_emotion_value(platform_id)
    
    # 基于平台特性生成回复模板
    responses = {
        "douyin": {
            "high": [
                ["哈哈哈哈", "这说到点子上了", "必须点赞！"],
                ["家人们", "这波我站你！", "太对了太对了"],
            ],
            "medium": [
                ["emmm", "有点道理", "但是吧..."],
                ["这个嘛", "各有各的看法呗"],
            ],
            "low": [
                ["..."],
                ["行吧", "你开心就好"],
                ["呵呵"],
            ]
        },
        "zhihu": {
            "high": [
                "这个观点很有见地。让我从专业角度补充几点：首先，从历史维度来看...",
                "非常认同。事实上，根据相关研究表明...",
            ],
            "medium": [
                "这个问题比较复杂。一方面...另一方面...",
                "先问是不是，再问为什么。你说的情况需要具体分析。",
            ],
            "low": [
                "...我觉得你可能对这个领域有些误解。",
                "建议先系统性地了解一下相关知识再来讨论。",
            ]
        },
        "xiaohongshu": {
            "high": [
                "天呐姐妹！！你说的也太对了吧！！✨💕 我之前也是这么想的！必须码住！",
                "绝绝子！！这个观点我要截图保存！！太有共鸣了呜呜呜 💗",
            ],
            "medium": [
                "嗯嗯有道理～不过我觉得可能还要看具体情况啦～ 🤔",
                "这个嘛...每个人想法不一样吧～ 尊重理解 💕",
            ],
            "low": [
                "...姐妹，咱能不能好好说话 😅",
                "这样说话真的好吗...有点伤人欸 💔",
            ]
        },
        "weibo": {
            "high": [
                "啊啊啊啊！！说的太好了！！#真相了# 转发转发！！",
                "救命！这话我要挂热搜！！太敢说了！！ #吃瓜#",
            ],
            "medium": [
                "emm 这事吧...两边都有道理？#中立吃瓜#",
                "不好说...坐等后续 #围观#",
            ],
            "low": [
                "......#无语#",
                "行 随便你 #告辞#",
            ]
        },
        "x": {
            "high": [
                "This is exactly what I've been saying. Great point! 👏",
                "Based take. Finally someone gets it.",
            ],
            "medium": [
                "Interesting perspective. Though I'd argue that...",
                "Fair point, but have you considered the global context?",
            ],
            "low": [
                "...I don't think you quite understand the nuance here.",
                "This take is so local. Try broadening your perspective.",
            ]
        },
        "tieba": {
            "high": [
                "乐，这下懂了",
                "典中典，给你点个赞",
            ],
            "medium": [
                "一般般吧",
                "行，有点东西",
            ],
            "low": [
                "绷不住了",
                "急了",
                "蚌埠住了",
            ]
        }
    }
    
    # 根据情绪选择回复等级
    if emotion_value >= 60:
        level = "high"
    elif emotion_value >= 30:
        level = "medium"
    else:
        level = "low"
    
    platform_responses = responses.get(platform_id, {}).get(level, ["..."])
    response = random.choice(platform_responses)
    
    # 抖音特殊处理：分条发送
    if platform_id == "douyin" and isinstance(response, list):
        return response
    elif isinstance(response, list):
        return " ".join(response)
    
    return response

def process_private_msg_choice(choice: int) -> Tuple[str, Optional[Dict]]:
    """处理私信选择"""
    if not session.pending_private_msg:
        return "", None
    
    result = session.private_msg_system.process_user_choice(
        session.pending_private_msg, 
        choice
    )
    
    # 记录行为到灵魂测试
    if session.soul_test:
        behavior_type = ["alliance", "neutral", "expose"][choice]
        session.soul_test.record_behavior(behavior_type, {
            "sender": session.pending_private_msg.get("sender"),
            "target": session.pending_private_msg.get("target")
        })
    
    session.pending_private_msg = None
    
    # 如果选择公开，返回公开消息
    if choice == 2 and result.get("exposed_message"):
        return result.get("exposed_message"), result
    
    return result.get("feedback", ""), result

def end_chat() -> Dict:
    """结束聊天，生成总结"""
    if not session.is_chatting:
        return {}
    
    session.is_chatting = False
    
    # 生成灵魂测试结果
    soul_result = None
    if session.soul_test:
        soul_result = session.soul_test.generate_analysis()
    
    # 生成平台私下评价
    platform_reviews = {}
    for platform_id in session.selected_platforms:
        platform_reviews[platform_id] = generate_platform_review(platform_id)
    
    # 获取破防集锦
    breakpoint_highlights = []
    if session.emotion_system:
        breakpoint_highlights = session.emotion_system.get_breakpoint_highlights()
    
    # 获取叛变记录
    betrayal_summary = []
    if session.betrayal_system:
        betrayal_summary = session.betrayal_system.get_betrayal_summary()
    
    return {
        "soul_result": soul_result,
        "platform_reviews": platform_reviews,
        "breakpoint_highlights": breakpoint_highlights,
        "betrayal_summary": betrayal_summary,
        "turn_count": session.turn_count,
        "topic": session.current_topic
    }

def generate_platform_review(platform_id: str) -> str:
    """生成平台对用户的私下评价"""
    reviews = {
        "douyin": [
            "这人有点意思，虽然话多了点，但至少不无聊",
            "还行吧，就是不太会玩梗，建议多刷刷视频",
            "话说的挺好的，但感觉不太上镜的样子"
        ],
        "zhihu": [
            "逻辑能力有待提高，建议系统性学习",
            "有自己的思考，但深度不够，继续努力",
            "还可以，至少愿意讨论问题而不是只会抬杠"
        ],
        "xiaohongshu": [
            "感觉是个有生活态度的人呢～ 虽然审美还需要培养 💕",
            "人还不错啦，就是发言不太有氛围感 🤔",
            "下次可以试试更精致的表达方式哦～ ✨"
        ],
        "weibo": [
            "这人挺敢说的，有当大V的潜质",
            "吃瓜态度不够积极，热度意识有待加强",
            "还行，至少不是那种无脑喷的"
        ],
        "x": [
            "Interesting person. Could use more global perspective though.",
            "Not bad, but seems a bit too locally focused.",
            "Has potential for meaningful discussions."
        ],
        "tieba": [
            "还行，不是很典",
            "有点东西，但不多",
            "乐，这人挺逗的"
        ]
    }
    
    return random.choice(reviews.get(platform_id, ["普通用户。"]))

# ==================== Gradio界面构建 ====================

def create_platform_selection_html() -> str:
    """创建平台选择HTML"""
    html = '<div class="platform-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; padding: 20px;">'
    
    for platform_id, name in PLATFORM_NAMES.items():
        avatar = PLATFORM_AVATARS[platform_id]
        color = PLATFORM_COLORS[platform_id]
        selected_class = "selected" if platform_id in session.selected_platforms else ""
        
        html += f'''
        <div class="platform-card {selected_class}" onclick="selectPlatform('{platform_id}')" style="
            background: white;
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 3px solid {'#667eea' if platform_id in session.selected_platforms else 'transparent'};
        ">
            <div style="font-size: 48px; margin-bottom: 10px;">{avatar}</div>
            <div style="font-size: 18px; font-weight: bold; color: {color};">{name}</div>
            <div style="font-size: 12px; color: #666; margin-top: 5px;">
                {PLATFORMS.get(platform_id, {}).get('personality', {}).get('age', '?')}岁 | 
                {PLATFORMS.get(platform_id, {}).get('personality', {}).get('mbti', '????')}
            </div>
        </div>
        '''
    
    html += '</div>'
    return html

def format_chat_message(msg: Dict) -> str:
    """格式化聊天消息为HTML"""
    role = msg.get("role", "")
    content = msg.get("content", "")
    
    if role == "system":
        return f'''
        <div style="text-align: center; padding: 10px; color: #666; font-style: italic;">
            {content}
        </div>
        '''
    elif role == "user":
        return f'''
        <div style="display: flex; justify-content: flex-end; margin: 8px 0;">
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 16px;
                border-radius: 18px 18px 4px 18px;
                max-width: 70%;
            ">
                {content}
            </div>
            <div style="margin-left: 8px; font-size: 24px;">👤</div>
        </div>
        '''
    elif role == "platform":
        platform_id = msg.get("platform_id", "")
        avatar = PLATFORM_AVATARS.get(platform_id, "🤖")
        color = PLATFORM_COLORS.get(platform_id, "#333")
        name = PLATFORM_NAMES.get(platform_id, "未知")
        
        is_breakpoint = msg.get("is_breakpoint", False)
        is_betrayal = msg.get("is_betrayal", False)
        
        extra_style = ""
        if is_breakpoint:
            extra_style = "border: 2px solid #ff4444; background: #fff0f0;"
        elif is_betrayal:
            extra_style = "border: 2px solid #ffd700; background: #fffef0;"
        
        return f'''
        <div style="display: flex; margin: 8px 0;">
            <div style="font-size: 24px; margin-right: 8px;">{avatar}</div>
            <div>
                <div style="font-size: 12px; color: {color}; font-weight: bold; margin-bottom: 4px;">
                    {name}
                    {'💔 破防了！' if is_breakpoint else ''}
                    {'⚡ 叛变！' if is_betrayal else ''}
                </div>
                <div style="
                    background: #f0f0f0;
                    padding: 12px 16px;
                    border-radius: 18px 18px 18px 4px;
                    max-width: 70%;
                    {extra_style}
                ">
                    {content}
                </div>
            </div>
        </div>
        '''
    
    return ""

def format_emotion_display() -> str:
    """格式化情绪显示"""
    if not session.emotion_system:
        return ""
    
    html = '<div style="display: flex; gap: 20px; padding: 10px;">'
    
    for platform_id in session.selected_platforms:
        value = session.emotion_system.get_emotion_value(platform_id)
        emoji = session.emotion_system.get_emotion_emoji(platform_id)
        name = PLATFORM_NAMES.get(platform_id, "")
        color = PLATFORM_COLORS.get(platform_id, "#333")
        
        # 情绪条颜色
        if value >= 60:
            bar_color = "linear-gradient(90deg, #4CAF50, #8BC34A)"
        elif value >= 30:
            bar_color = "linear-gradient(90deg, #FFC107, #FF9800)"
        else:
            bar_color = "linear-gradient(90deg, #f44336, #E91E63)"
        
        html += f'''
        <div style="flex: 1; background: white; padding: 10px; border-radius: 8px;">
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <span style="font-size: 20px; margin-right: 5px;">{PLATFORM_AVATARS.get(platform_id, "")}</span>
                <span style="color: {color}; font-weight: bold;">{name}</span>
                <span style="margin-left: auto;">{emoji} {value}%</span>
            </div>
            <div style="height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden;">
                <div style="height: 100%; width: {value}%; background: {bar_color}; border-radius: 4px;"></div>
            </div>
        </div>
        '''
    
    html += '</div>'
    return html

def format_private_msg_popup(msg: Dict) -> str:
    """格式化私信弹窗"""
    if not msg:
        return ""
    
    sender = msg.get("sender", "")
    sender_name = PLATFORM_NAMES.get(sender, "")
    sender_avatar = PLATFORM_AVATARS.get(sender, "")
    content = msg.get("content", "")
    options = msg.get("options", [])
    
    html = f'''
    <div style="
        background: white;
        border-radius: 16px;
        padding: 24px;
        max-width: 400px;
        margin: 20px auto;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    ">
        <div style="display: flex; align-items: center; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #eee;">
            <span style="font-size: 32px; margin-right: 10px;">{sender_avatar}</span>
            <div>
                <div style="font-weight: bold;">{sender_name}</div>
                <div style="font-size: 12px; color: #666;">私信 · 仅你可见</div>
            </div>
        </div>
        <div style="font-size: 1.1em; line-height: 1.6; margin-bottom: 20px;">
            {content}
        </div>
        <div>
    '''
    
    for i, option in enumerate(options):
        colors = ["#4CAF50", "#9E9E9E", "#f44336"]
        html += f'''
        <button onclick="handlePrivateChoice({i})" style="
            width: 100%;
            padding: 12px;
            margin: 8px 0;
            border-radius: 8px;
            border: none;
            background: {colors[i]};
            color: white;
            cursor: pointer;
            font-size: 14px;
        ">
            {option}
        </button>
        '''
    
    html += '</div></div>'
    return html

def format_summary(summary: Dict) -> str:
    """格式化总结页面"""
    if not summary:
        return ""
    
    soul_result = summary.get("soul_result", {})
    platform_reviews = summary.get("platform_reviews", {})
    
    html = '<div style="background: white; border-radius: 20px; padding: 30px; margin: 20px;">'
    
    # 标题
    html += f'''
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #667eea;">🎭 对话总结</h1>
        <p style="color: #666;">话题: {summary.get("topic", "")} | 对话轮数: {summary.get("turn_count", 0)}</p>
    </div>
    '''
    
    # 灵魂测试结果
    if soul_result:
        scores = soul_result.get("scores", {})
        soul_type = soul_result.get("soul_type", {})
        
        html += '''
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            padding: 30px;
            color: white;
            margin-bottom: 30px;
        ">
            <h2 style="text-align: center; margin-bottom: 20px;">🔮 灵魂纯度测试结果</h2>
        '''
        
        html += f'''
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 24px; font-weight: bold;">{soul_type.get("name", "未知灵魂")}</div>
                <div style="font-size: 14px; opacity: 0.8; margin-top: 5px;">{soul_type.get("description", "")}</div>
            </div>
        '''
        
        # 平台占比条
        html += '<div style="margin-top: 20px;">'
        for platform_id, score in scores.items():
            name = PLATFORM_NAMES.get(platform_id, platform_id)
            color = PLATFORM_COLORS.get(platform_id, "#333")
            html += f'''
            <div style="display: flex; align-items: center; margin: 10px 0;">
                <span style="width: 80px; font-weight: bold;">{name}</span>
                <div style="flex: 1; height: 24px; background: rgba(255,255,255,0.2); border-radius: 12px; overflow: hidden;">
                    <div style="
                        height: 100%;
                        width: {score}%;
                        background: {color};
                        border-radius: 12px;
                        display: flex;
                        align-items: center;
                        justify-content: flex-end;
                        padding-right: 10px;
                        font-size: 12px;
                    ">{score:.1f}%</div>
                </div>
            </div>
            '''
        html += '</div>'
        
        # 毒舌点评
        roast = soul_result.get("roast", "")
        if roast:
            html += f'''
            <div style="margin-top: 20px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px;">
                <div style="font-weight: bold; margin-bottom: 10px;">💬 毒舌点评</div>
                <div>{roast}</div>
            </div>
            '''
        
        html += '</div>'
    
    # 平台私下评价
    html += '''
    <div style="margin-top: 30px;">
        <h3 style="color: #333; margin-bottom: 15px;">🤫 平台私下评价</h3>
    '''
    for platform_id, review in platform_reviews.items():
        name = PLATFORM_NAMES.get(platform_id, platform_id)
        avatar = PLATFORM_AVATARS.get(platform_id, "")
        color = PLATFORM_COLORS.get(platform_id, "#333")
        html += f'''
        <div style="
            background: #f5f5f5;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            display: flex;
            align-items: flex-start;
        ">
            <span style="font-size: 24px; margin-right: 10px;">{avatar}</span>
            <div>
                <div style="font-weight: bold; color: {color};">{name}</div>
                <div style="color: #666; margin-top: 5px;">{review}</div>
            </div>
        </div>
        '''
    html += '</div>'
    
    # 破防集锦
    breakpoints = summary.get("breakpoint_highlights", [])
    if breakpoints:
        html += '''
        <div style="margin-top: 30px;">
            <h3 style="color: #333; margin-bottom: 15px;">💔 破防名场面</h3>
        '''
        for bp in breakpoints:
            html += f'''
            <div style="
                background: #fff0f0;
                border: 1px solid #ffcccc;
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
            ">
                <div style="font-weight: bold; color: #ff4444;">{PLATFORM_NAMES.get(bp.get('platform_id', ''), '')} 破防了！</div>
                <div style="margin-top: 10px;">"{bp.get('response', '')}"</div>
            </div>
            '''
        html += '</div>'
    
    html += '</div>'
    return html

# ==================== 主界面 ====================

def create_app():
    """创建Gradio应用"""
    
    with gr.Blocks(css=CUSTOM_CSS, title="平台人格群聊", theme=gr.themes.Soft()) as app:
        
        # 状态变量
        state = gr.State(value={})
        
        # 标题
        gr.HTML('''
        <div style="text-align: center; padding: 20px;">
            <h1 style="font-size: 2.5em; color: #333; margin-bottom: 10px;">🎭 平台人格群聊系统</h1>
            <p style="color: #666;">选择两个平台，开启一场跨次元的灵魂碰撞！</p>
        </div>
        ''')
        
        with gr.Tabs() as tabs:
            
            # ===== 选择平台 Tab =====
            with gr.Tab("1️⃣ 选择平台", id="tab_select"):
                gr.Markdown("### 请选择两个平台参与讨论")
                
                with gr.Row():
                    for platform_id in list(PLATFORM_NAMES.keys())[:3]:
                        with gr.Column():
                            btn = gr.Button(
                                f"{PLATFORM_AVATARS[platform_id]} {PLATFORM_NAMES[platform_id]}",
                                variant="secondary",
                                elem_id=f"btn_{platform_id}"
                            )
                
                with gr.Row():
                    for platform_id in list(PLATFORM_NAMES.keys())[3:]:
                        with gr.Column():
                            btn = gr.Button(
                                f"{PLATFORM_AVATARS[platform_id]} {PLATFORM_NAMES[platform_id]}",
                                variant="secondary",
                                elem_id=f"btn_{platform_id}"
                            )
                
                selected_display = gr.Textbox(
                    label="已选择",
                    value="请选择两个平台",
                    interactive=False
                )
                
                start_btn = gr.Button("开始选话题 ▶", variant="primary", visible=False)
            
            # ===== 选择话题 Tab =====
            with gr.Tab("2️⃣ 选择话题", id="tab_topic"):
                gr.Markdown("### 选择一个话题开始讨论")
                
                topic_buttons = []
                with gr.Column():
                    for i in range(3):
                        topic_btn = gr.Button(f"话题 {i+1}", visible=False)
                        topic_buttons.append(topic_btn)
                
                refresh_btn = gr.Button("🔄 换一批话题", variant="secondary")
                topic_display = gr.Textbox(label="当前话题", interactive=False, visible=False)
            
            # ===== 群聊 Tab =====
            with gr.Tab("3️⃣ 群聊", id="tab_chat"):
                # 情绪条显示
                emotion_display = gr.HTML("")
                
                # 聊天区域
                chatbot = gr.Chatbot(
                    label="群聊",
                    height=400,
                    type="messages"
                )
                
                # 私信弹窗
                private_msg_box = gr.HTML("", visible=False)
                with gr.Row(visible=False) as private_choice_row:
                    choice_0 = gr.Button("配合 ✅")
                    choice_1 = gr.Button("中立 😐")
                    choice_2 = gr.Button("公开 📢")
                
                # 输入区域
                with gr.Row():
                    user_input = gr.Textbox(
                        placeholder="说点什么...",
                        show_label=False,
                        scale=4
                    )
                    send_btn = gr.Button("发送", variant="primary", scale=1)
                
                with gr.Row():
                    voice_toggle = gr.Checkbox(label="🔊 语音播放", value=False)
                    end_btn = gr.Button("结束对话", variant="stop")
            
            # ===== 总结 Tab =====
            with gr.Tab("4️⃣ 总结", id="tab_summary"):
                summary_html = gr.HTML("")
                restart_btn = gr.Button("🔄 重新开始", variant="primary")
        
        # ==================== 事件处理 ====================
        
        def handle_platform_select(platform_id, current_state):
            """处理平台选择"""
            selected = current_state.get("selected_platforms", [])
            
            if platform_id in selected:
                selected.remove(platform_id)
            elif len(selected) < 2:
                selected.append(platform_id)
            
            current_state["selected_platforms"] = selected
            
            # 更新显示
            if len(selected) == 0:
                display_text = "请选择两个平台"
                show_start = False
            elif len(selected) == 1:
                display_text = f"已选择: {PLATFORM_NAMES[selected[0]]}，请再选一个"
                show_start = False
            else:
                display_text = f"已选择: {PLATFORM_NAMES[selected[0]]} vs {PLATFORM_NAMES[selected[1]]}"
                show_start = True
            
            return current_state, display_text, gr.update(visible=show_start)
        
        def handle_refresh_topics(current_state):
            """刷新话题"""
            topics = get_random_topics(3)
            current_state["available_topics"] = topics
            
            updates = []
            for i, topic in enumerate(topics):
                updates.append(gr.update(
                    value=f"🔥 {topic['title']}",
                    visible=True
                ))
            
            return [current_state] + updates
        
        def handle_topic_select(topic_idx, current_state):
            """处理话题选择"""
            topics = current_state.get("available_topics", [])
            if topic_idx < len(topics):
                selected_topic = topics[topic_idx]
                current_state["current_topic"] = selected_topic["title"]
                
                # 初始化会话
                session.selected_platforms = current_state.get("selected_platforms", [])
                start_chat(selected_topic["title"])
                
                # 生成初始消息
                messages = []
                for msg in session.chat_history:
                    if msg["role"] == "system":
                        messages.append({"role": "assistant", "content": f"📢 {msg['content']}"})
                    elif msg["role"] == "platform":
                        platform_id = msg.get("platform_id", "")
                        avatar = PLATFORM_AVATARS.get(platform_id, "🤖")
                        name = PLATFORM_NAMES.get(platform_id, "")
                        messages.append({"role": "assistant", "content": f"{avatar} **{name}**: {msg['content']}"})
                
                emotion_html = format_emotion_display()
                
                return (
                    current_state,
                    gr.update(value=selected_topic["title"], visible=True),
                    messages,
                    emotion_html,
                    gr.update(selected="tab_chat")
                )
            
            return current_state, gr.update(), [], "", gr.update()
        
        def handle_send_message(message, history, current_state):
            """处理发送消息"""
            if not message.strip():
                return "", history, "", gr.update(visible=False), gr.update(visible=False), current_state
            
            # 处理用户消息
            new_messages, private_msg, effect = process_user_message(message)
            
            # 更新聊天记录
            history.append({"role": "user", "content": message})
            
            for msg in new_messages:
                if msg["role"] == "platform":
                    platform_id = msg.get("platform_id", "")
                    avatar = PLATFORM_AVATARS.get(platform_id, "🤖")
                    name = PLATFORM_NAMES.get(platform_id, "")
                    
                    prefix = ""
                    if msg.get("is_breakpoint"):
                        prefix = "💔 [破防] "
                    elif msg.get("is_betrayal"):
                        prefix = "⚡ [叛变] "
                    
                    history.append({
                        "role": "assistant",
                        "content": f"{avatar} **{name}**: {prefix}{msg['content']}"
                    })
            
            # 更新情绪显示
            emotion_html = format_emotion_display()
            
            # 处理私信
            if private_msg:
                current_state["pending_private_msg"] = private_msg
                private_html = format_private_msg_popup(private_msg)
                return "", history, emotion_html, gr.update(value=private_html, visible=True), gr.update(visible=True), current_state
            
            return "", history, emotion_html, gr.update(visible=False), gr.update(visible=False), current_state
        
        def handle_private_choice(choice, history, current_state):
            """处理私信选择"""
            result_text, result = process_private_msg_choice(choice)
            
            if choice == 2 and result and result.get("exposed_message"):
                # 公开到群里
                history.append({
                    "role": "assistant",
                    "content": f"📢 **系统**: {result.get('exposed_message')}"
                })
            elif result_text:
                history.append({
                    "role": "assistant",
                    "content": f"🔒 **私信回复**: {result_text}"
                })
            
            current_state["pending_private_msg"] = None
            emotion_html = format_emotion_display()
            
            return history, emotion_html, gr.update(visible=False), gr.update(visible=False), current_state
        
        def handle_end_chat(current_state):
            """结束对话"""
            summary = end_chat()
            summary_html_content = format_summary(summary)
            
            return summary_html_content, gr.update(selected="tab_summary")
        
        def handle_restart():
            """重新开始"""
            initialize_session()
            return (
                {},
                "请选择两个平台",
                gr.update(visible=False),
                [],
                "",
                "",
                gr.update(selected="tab_select")
            )
        
        # ===== 绑定事件 =====
        
        # 平台选择按钮
        for platform_id in PLATFORM_NAMES.keys():
            # 由于Gradio的限制，这里使用简化的方式
            pass
        
        # 这里简化处理，实际使用时需要为每个按钮单独绑定
        refresh_btn.click(
            handle_refresh_topics,
            inputs=[state],
            outputs=[state] + topic_buttons
        )
        
        # 发送消息
        send_btn.click(
            handle_send_message,
            inputs=[user_input, chatbot, state],
            outputs=[user_input, chatbot, emotion_display, private_msg_box, private_choice_row, state]
        )
        
        user_input.submit(
            handle_send_message,
            inputs=[user_input, chatbot, state],
            outputs=[user_input, chatbot, emotion_display, private_msg_box, private_choice_row, state]
        )
        
        # 私信选择
        choice_0.click(
            lambda h, s: handle_private_choice(0, h, s),
            inputs=[chatbot, state],
            outputs=[chatbot, emotion_display, private_msg_box, private_choice_row, state]
        )
        choice_1.click(
            lambda h, s: handle_private_choice(1, h, s),
            inputs=[chatbot, state],
            outputs=[chatbot, emotion_display, private_msg_box, private_choice_row, state]
        )
        choice_2.click(
            lambda h, s: handle_private_choice(2, h, s),
            inputs=[chatbot, state],
            outputs=[chatbot, emotion_display, private_msg_box, private_choice_row, state]
        )
        
        # 结束对话
        end_btn.click(
            handle_end_chat,
            inputs=[state],
            outputs=[summary_html, tabs]
        )
        
        # 重新开始
        restart_btn.click(
            handle_restart,
            outputs=[state, selected_display, start_btn, chatbot, emotion_display, summary_html, tabs]
        )
        
        # 初始化
        app.load(
            handle_refresh_topics,
            inputs=[state],
            outputs=[state] + topic_buttons
        )
    
    return app

# ==================== 入口 ====================

if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
