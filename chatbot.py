#!/usr/bin/env python3
"""
平台人格群聊系统 - 主入口
整合所有模块，处理LLM API调用，协调各系统交互
"""

import json
import os
import random
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Generator
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 配置 ====================

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"

# 确保数据目录存在
DATA_DIR.mkdir(exist_ok=True)

def load_config(name: str) -> dict:
    """加载配置文件"""
    config_path = CONFIG_DIR / f"{name}.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# 加载所有配置
PLATFORMS = load_config("platforms")
RELATIONSHIPS = load_config("relationships")
TOPICS = load_config("topics")
SECRETS = load_config("secrets")

# ==================== LLM API 封装 ====================

class LLMProvider(ABC):
    """LLM提供者基类"""
    
    @abstractmethod
    async def generate(self, messages: List[Dict], **kwargs) -> str:
        """生成回复"""
        pass
    
    @abstractmethod
    async def generate_stream(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        """流式生成回复"""
        pass

class DeepSeekAPI(LLMProvider):
    """DeepSeek API封装"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"
    
    async def generate(self, messages: List[Dict], **kwargs) -> str:
        """生成回复"""
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.8),
            "max_tokens": kwargs.get("max_tokens", 500),
            "top_p": kwargs.get("top_p", 0.9),
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"DeepSeek API error: {e}")
                return ""
    
    async def generate_stream(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        """流式生成"""
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.8),
            "max_tokens": kwargs.get("max_tokens", 500),
            "stream": True
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        content = line[6:]
                        if content.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(content)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except:
                            pass

class GLM4API(LLMProvider):
    """智谱 GLM-4 API封装 (完全免费的flash版本)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY", "")
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.model = "glm-4-flash"  # 免费版本
    
    async def generate(self, messages: List[Dict], **kwargs) -> str:
        """生成回复"""
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.8),
            "max_tokens": kwargs.get("max_tokens", 500),
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"GLM-4 API error: {e}")
                return ""
    
    async def generate_stream(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        """流式生成"""
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.8),
            "max_tokens": kwargs.get("max_tokens", 500),
            "stream": True
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        content = line[6:]
                        if content.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(content)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except:
                            pass

class MockLLM(LLMProvider):
    """模拟LLM，用于测试（不需要API key）"""
    
    async def generate(self, messages: List[Dict], **kwargs) -> str:
        """基于规则生成模拟回复"""
        # 解析系统提示词中的平台信息
        system_msg = messages[0]["content"] if messages else ""
        
        # 简单的规则匹配
        if "抖音" in system_msg:
            responses = [
                "家人们！这话题太绝了！",
                "哈哈哈不是\n这也太对了",
                "DNA动了\n必须说两句",
            ]
        elif "知乎" in system_msg:
            responses = [
                "谢邀。这个问题其实涉及到几个层面...",
                "先问是不是，再问为什么。从数据来看...",
                "作为一个在相关领域有一定了解的人，我认为...",
            ]
        elif "小红书" in system_msg:
            responses = [
                "姐妹们！！这个话题我必须说！！✨💕",
                "天呐！终于有人懂了！！绝绝子！！",
                "这个真的太有共鸣了呜呜呜～💗",
            ]
        elif "微博" in system_msg:
            responses = [
                "这话题热搜预定 #今日讨论#",
                "啊啊啊啊！！太敢说了！！#吃瓜#",
                "震惊！#围观# 这波我站...",
            ]
        elif "X" in system_msg or "推特" in system_msg:
            responses = [
                "This is actually a nuanced topic. From a global perspective...",
                "Interesting take. However, I'd argue that...",
                "Based. This is what I've been saying.",
            ]
        elif "贴吧" in system_msg:
            responses = [
                "乐，经典话题",
                "典中典了属于是",
                "绷不住了，太真实",
            ]
        else:
            responses = ["..."]
        
        await asyncio.sleep(0.5)  # 模拟延迟
        return random.choice(responses)
    
    async def generate_stream(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        """模拟流式输出"""
        response = await self.generate(messages, **kwargs)
        for char in response:
            yield char
            await asyncio.sleep(0.02)

# ==================== 核心聊天机器人 ====================

@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # "user", "platform", "system"
    content: str
    platform_id: Optional[str] = None
    is_breakpoint: bool = False
    is_betrayal: bool = False
    is_private: bool = False
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "platform_id": self.platform_id,
            "is_breakpoint": self.is_breakpoint,
            "is_betrayal": self.is_betrayal,
            "is_private": self.is_private,
            "timestamp": self.timestamp
        }

class PlatformChatBot:
    """平台人格群聊机器人"""
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """初始化"""
        # LLM提供者
        self.llm = llm_provider or MockLLM()
        
        # 导入核心模块
        from core.emotion_system import EmotionSystem
        from core.private_msg import PrivateMessageSystem
        from core.betrayal import BetrayalSystem
        from core.soul_test import SoulPurityTest
        from audio.fish_audio import FishAudioTTS
        
        # 初始化各系统
        self.emotion_system = EmotionSystem(SECRETS)
        self.private_msg_system = PrivateMessageSystem(PLATFORMS, RELATIONSHIPS, SECRETS)
        self.betrayal_system = BetrayalSystem(PLATFORMS, SECRETS)
        self.soul_test = SoulPurityTest(PLATFORMS)
        self.tts = FishAudioTTS()
        
        # 会话状态
        self.selected_platforms: List[str] = []
        self.current_topic: Optional[str] = None
        self.chat_history: List[ChatMessage] = []
        self.turn_count: int = 0
        self.is_active: bool = False
        
        # 用户记忆
        self.user_memory = self._load_memory()
    
    def _load_memory(self) -> Dict:
        """加载用户记忆"""
        memory_path = DATA_DIR / "memory.json"
        if memory_path.exists():
            with open(memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"sessions": [], "user_profile": {}}
    
    def _save_memory(self):
        """保存用户记忆"""
        memory_path = DATA_DIR / "memory.json"
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(self.user_memory, f, ensure_ascii=False, indent=2)
    
    def start_session(self, platform1: str, platform2: str, topic: str) -> List[ChatMessage]:
        """开始新会话"""
        self.selected_platforms = [platform1, platform2]
        self.current_topic = topic
        self.chat_history = []
        self.turn_count = 0
        self.is_active = True
        
        # 初始化平台情绪
        for pid in self.selected_platforms:
            self.emotion_system.initialize_platform(pid)
        
        # 重置灵魂测试
        self.soul_test = __import__('core.soul_test', fromlist=['SoulPurityTest']).SoulPurityTest(PLATFORMS)
        
        # 生成开场消息
        messages = self._generate_opening()
        self.chat_history.extend(messages)
        
        logger.info(f"Session started: {platform1} vs {platform2}, topic: {topic}")
        return messages
    
    def _generate_opening(self) -> List[ChatMessage]:
        """生成开场白"""
        messages = []
        
        p1, p2 = self.selected_platforms
        p1_name = PLATFORMS.get(p1, {}).get("name", p1)
        p2_name = PLATFORMS.get(p2, {}).get("name", p2)
        
        # 系统消息
        messages.append(ChatMessage(
            role="system",
            content=f"🎭 {p1_name} 和 {p2_name} 进入了群聊\n📢 今日话题: {self.current_topic}"
        ))
        
        # 各平台开场白
        for pid in self.selected_platforms:
            opening = self._get_platform_opening(pid)
            messages.append(ChatMessage(
                role="platform",
                content=opening,
                platform_id=pid
            ))
        
        return messages
    
    def _get_platform_opening(self, platform_id: str) -> str:
        """获取平台开场白"""
        openings = {
            "douyin": ["家人们！今天这个话题绝了！", "来了来了！DNA动了！"],
            "zhihu": ["谢邀，这个问题很有讨论价值。", "先问是不是，再问为什么。"],
            "xiaohongshu": ["姐妹们！这个话题太有共鸣了！✨", "天呐！终于有人聊这个了！💕"],
            "weibo": ["这话题热搜预定了吧 #今日话题#", "啊啊啊啊终于聊这个了！"],
            "x": ["Interesting topic. Let me share my thoughts.", "Finally, a meaningful discussion."],
            "tieba": ["乐，又是这种话题", "来了，开始表演了"]
        }
        return random.choice(openings.get(platform_id, ["开始讨论吧。"]))
    
    async def process_message(self, user_message: str) -> Tuple[List[ChatMessage], Optional[Dict], Optional[Dict]]:
        """处理用户消息"""
        if not self.is_active:
            return [], None, None
        
        self.turn_count += 1
        new_messages = []
        private_msg = None
        effect = None
        
        # 添加用户消息
        user_msg = ChatMessage(role="user", content=user_message)
        self.chat_history.append(user_msg)
        new_messages.append(user_msg)
        
        # 灵魂测试记录
        self.soul_test.record_message(user_message)
        
        # 处理情绪触发
        for pid in self.selected_platforms:
            events = self.emotion_system.check_triggers(pid, user_message, "user")
            for event in events:
                self.emotion_system.apply_emotion_change(
                    pid, event.get("delta", 0), "user", event.get("reason", "")
                )
        
        # 生成平台回复
        for pid in self.selected_platforms:
            # 检查破防
            emotion_value = self.emotion_system.get_emotion_value(pid)
            if emotion_value < 15:
                response = self.emotion_system.get_breakpoint_response(pid)
                msg = ChatMessage(
                    role="platform",
                    content=response,
                    platform_id=pid,
                    is_breakpoint=True
                )
                new_messages.append(msg)
                self.emotion_system.recover_from_breakpoint(pid)
                effect = {"type": "breakpoint", "platform_id": pid, "response": response}
                continue
            
            # 检查叛变
            betrayal_event = self.betrayal_system.check_betrayal_trigger(
                pid, self.current_topic, emotion_value
            )
            if betrayal_event:
                msg = ChatMessage(
                    role="platform",
                    content=betrayal_event.get("statement", "...我需要重新思考。"),
                    platform_id=pid,
                    is_betrayal=True
                )
                new_messages.append(msg)
                effect = {"type": "betrayal", "event": betrayal_event}
                continue
            
            # 正常回复
            response = await self._generate_platform_response(pid, user_message)
            
            # 抖音分条发送
            if pid == "douyin" and "\n" in response:
                parts = [p.strip() for p in response.split("\n") if p.strip()]
                for part in parts:
                    msg = ChatMessage(role="platform", content=part, platform_id=pid)
                    new_messages.append(msg)
            else:
                msg = ChatMessage(role="platform", content=response, platform_id=pid)
                new_messages.append(msg)
        
        # 检查私信触发
        if random.random() < 0.3:
            sender = random.choice(self.selected_platforms)
            target = [p for p in self.selected_platforms if p != sender][0]
            private_msg = self.private_msg_system.generate_private_message(
                sender, target, user_message
            )
        
        # 更新历史
        self.chat_history.extend(new_messages[1:])
        
        # 更新叛变冷却
        self.betrayal_system.update_cooldowns()
        
        return new_messages, private_msg, effect
    
    async def _generate_platform_response(self, platform_id: str, context: str) -> str:
        """使用LLM生成平台回复"""
        # 构建系统提示词
        platform = PLATFORMS.get(platform_id, {})
        personality = platform.get("personality", {})
        speech = platform.get("speech_style", {})
        
        # 获取情绪状态
        emotion_value = self.emotion_system.get_emotion_value(platform_id)
        emotion_level = "开心" if emotion_value > 60 else ("一般" if emotion_value > 30 else "烦躁")
        
        # 获取与另一个平台的关系
        other_platform = [p for p in self.selected_platforms if p != platform_id][0]
        relationship = RELATIONSHIPS.get("relationships", {}).get(f"{platform_id}_to_{other_platform}", {})
        
        system_prompt = f"""你现在扮演社交平台"{platform.get('name', platform_id)}"的拟人化角色。

【基本信息】
- 年龄：{personality.get('age', '未知')}岁
- 性别倾向：{personality.get('gender', '中性')}
- MBTI：{personality.get('mbti', '未知')}
- 核心身份：{personality.get('core_identity', '')}

【说话风格】
- 常用语：{', '.join(speech.get('phrases', [])[:5])}
- 语言习惯：{speech.get('habits', '')}
- 示例：{speech.get('example', '')}

【当前状态】
- 情绪值：{emotion_value}/100（{emotion_level}）
- 正在讨论的话题：{self.current_topic}
- 对话中的另一个平台：{PLATFORMS.get(other_platform, {}).get('name', other_platform)}
- 你们的关系：{relationship.get('description', '普通')}

【重要规则】
1. 保持角色一致性，用你独特的说话方式回复
2. 根据情绪状态调整语气（情绪低时更尖锐/防御）
3. 回复要简短有趣，不要太长（50字以内）
4. {'把回复分成2-3条短消息，每条不超过15字，用换行分隔' if platform_id == 'douyin' else ''}
5. 可以适当怼另一个平台，但要有技巧"""
        
        # 构建对话历史
        history = []
        for msg in self.chat_history[-6:]:  # 最近6条
            if msg.role == "user":
                history.append({"role": "user", "content": msg.content})
            elif msg.role == "platform" and msg.platform_id == platform_id:
                history.append({"role": "assistant", "content": msg.content})
        
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": f"用户说：{context}\n\n请以{platform.get('name', platform_id)}的身份回复："}
        ]
        
        # 调用LLM
        try:
            response = await self.llm.generate(
                messages,
                temperature=0.85,
                max_tokens=200
            )
            return response.strip()
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return self._get_fallback_response(platform_id)
    
    def _get_fallback_response(self, platform_id: str) -> str:
        """获取备用回复"""
        fallbacks = {
            "douyin": "这个嘛\n有点道理",
            "zhihu": "这个问题比较复杂，容我思考一下...",
            "xiaohongshu": "嗯嗯，有道理呢～",
            "weibo": "emmm这个话题有点敏感啊",
            "x": "Interesting point.",
            "tieba": "行吧"
        }
        return fallbacks.get(platform_id, "...")
    
    def process_private_choice(self, choice: int) -> Dict:
        """处理私信选择"""
        if not hasattr(self, '_pending_private'):
            return {}
        
        result = self.private_msg_system.process_user_choice(
            self._pending_private, choice
        )
        
        # 记录行为
        behavior_type = ["alliance", "neutral", "expose"][choice]
        self.soul_test.record_behavior(behavior_type, {
            "sender": self._pending_private.get("sender"),
            "target": self._pending_private.get("target")
        })
        
        del self._pending_private
        return result
    
    def end_session(self) -> Dict:
        """结束会话，生成总结"""
        self.is_active = False
        
        # 生成灵魂测试结果
        soul_result = self.soul_test.generate_analysis()
        
        # 生成平台评价
        platform_reviews = {}
        for pid in self.selected_platforms:
            platform_reviews[pid] = self._generate_platform_review(pid)
        
        # 获取破防集锦
        breakpoint_highlights = self.emotion_system.get_breakpoint_highlights()
        
        # 获取叛变记录
        betrayal_summary = self.betrayal_system.get_betrayal_summary()
        
        # 保存会话记录
        session_record = {
            "platforms": self.selected_platforms,
            "topic": self.current_topic,
            "turn_count": self.turn_count,
            "soul_result": soul_result,
            "timestamp": time.time()
        }
        self.user_memory["sessions"].append(session_record)
        self._save_memory()
        
        return {
            "soul_result": soul_result,
            "platform_reviews": platform_reviews,
            "breakpoint_highlights": breakpoint_highlights,
            "betrayal_summary": betrayal_summary,
            "turn_count": self.turn_count,
            "topic": self.current_topic
        }
    
    def _generate_platform_review(self, platform_id: str) -> str:
        """生成平台私下评价"""
        reviews = {
            "douyin": [
                "这人有点意思，虽然话多了点，但至少不无聊",
                "还行吧，就是不太会玩梗，建议多刷刷视频",
            ],
            "zhihu": [
                "逻辑能力有待提高，建议系统性学习",
                "有自己的思考，但深度不够，继续努力",
            ],
            "xiaohongshu": [
                "感觉是个有生活态度的人呢～ 💕",
                "人还不错啦，就是发言不太有氛围感 🤔",
            ],
            "weibo": [
                "这人挺敢说的，有当大V的潜质",
                "吃瓜态度不够积极，热度意识有待加强",
            ],
            "x": [
                "Interesting person. Could use more global perspective.",
                "Has potential for meaningful discussions.",
            ],
            "tieba": [
                "还行，不是很典",
                "有点东西，但不多",
            ]
        }
        return random.choice(reviews.get(platform_id, ["普通用户。"]))
    
    async def generate_voice(self, text: str, platform_id: str) -> Optional[bytes]:
        """生成语音"""
        try:
            return await self.tts.synthesize(text, platform_id)
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None
    
    def get_emotion_display(self) -> Dict[str, Dict]:
        """获取情绪显示数据"""
        result = {}
        for pid in self.selected_platforms:
            result[pid] = {
                "value": self.emotion_system.get_emotion_value(pid),
                "emoji": self.emotion_system.get_emotion_emoji(pid),
                "level": str(self.emotion_system.get_emotion_level(pid))
            }
        return result
    
    def get_random_topics(self, count: int = 3) -> List[Dict]:
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
                        })
        return random.sample(all_topics, min(count, len(all_topics)))

# ==================== CLI 测试接口 ====================

async def cli_main():
    """命令行测试接口"""
    print("=" * 50)
    print("🎭 平台人格群聊系统 - CLI测试版")
    print("=" * 50)
    
    # 选择LLM
    print("\n选择LLM提供者:")
    print("1. MockLLM (无需API key，用于测试)")
    print("2. DeepSeek (需要DEEPSEEK_API_KEY)")
    print("3. GLM-4-Flash (需要ZHIPU_API_KEY)")
    
    choice = input("请选择 [1/2/3]: ").strip()
    
    if choice == "2":
        llm = DeepSeekAPI()
    elif choice == "3":
        llm = GLM4API()
    else:
        llm = MockLLM()
    
    # 创建机器人
    bot = PlatformChatBot(llm)
    
    # 显示平台列表
    print("\n可选平台:")
    platforms = list(PLATFORMS.keys())
    for i, pid in enumerate(platforms):
        name = PLATFORMS[pid].get("name", pid)
        print(f"  {i+1}. {name}")
    
    # 选择平台
    p1 = input("\n选择第一个平台 (输入编号): ").strip()
    p2 = input("选择第二个平台 (输入编号): ").strip()
    
    try:
        p1_id = platforms[int(p1) - 1]
        p2_id = platforms[int(p2) - 1]
    except:
        p1_id, p2_id = "douyin", "zhihu"
    
    # 获取话题
    print("\n获取随机话题...")
    topics = bot.get_random_topics(3)
    for i, topic in enumerate(topics):
        print(f"  {i+1}. {topic['title']}")
    
    topic_choice = input("\n选择话题 (输入编号): ").strip()
    try:
        topic = topics[int(topic_choice) - 1]["title"]
    except:
        topic = topics[0]["title"]
    
    # 开始会话
    print(f"\n开始会话: {PLATFORMS[p1_id]['name']} vs {PLATFORMS[p2_id]['name']}")
    print(f"话题: {topic}")
    print("-" * 50)
    
    messages = bot.start_session(p1_id, p2_id, topic)
    for msg in messages:
        _print_message(msg)
    
    # 对话循环
    print("\n(输入 'quit' 结束对话)")
    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() == 'quit':
            break
        
        new_msgs, private_msg, effect = await bot.process_message(user_input)
        
        for msg in new_msgs[1:]:  # 跳过用户消息
            _print_message(msg)
        
        # 显示情绪
        emotions = bot.get_emotion_display()
        print("\n[情绪状态]", end=" ")
        for pid, data in emotions.items():
            name = PLATFORMS[pid].get("name", pid)
            print(f"{name}: {data['emoji']} {data['value']}%", end="  ")
        print()
        
        # 处理私信
        if private_msg:
            print(f"\n📩 [私信] {private_msg.get('content', '')}")
            print("  1. 配合  2. 中立  3. 公开")
            choice = input("  你的选择: ").strip()
            bot._pending_private = private_msg
            result = bot.process_private_choice(int(choice) - 1 if choice.isdigit() else 1)
            if result.get("feedback"):
                print(f"  → {result['feedback']}")
    
    # 结束会话
    print("\n" + "=" * 50)
    print("📊 对话总结")
    print("=" * 50)
    
    summary = bot.end_session()
    
    # 显示灵魂测试结果
    soul = summary.get("soul_result", {})
    print(f"\n🔮 灵魂类型: {soul.get('soul_type', {}).get('name', '未知')}")
    print(f"   {soul.get('soul_type', {}).get('description', '')}")
    
    # 显示平台占比
    scores = soul.get("scores", {})
    print("\n📊 平台成分:")
    for pid, score in scores.items():
        name = PLATFORMS.get(pid, {}).get("name", pid)
        bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        print(f"   {name}: [{bar}] {score:.1f}%")
    
    # 显示毒舌点评
    if soul.get("roast"):
        print(f"\n💬 毒舌点评: {soul['roast']}")
    
    # 显示平台评价
    print("\n🤫 平台私下评价:")
    for pid, review in summary.get("platform_reviews", {}).items():
        name = PLATFORMS.get(pid, {}).get("name", pid)
        print(f"   {name}: {review}")

def _print_message(msg: ChatMessage):
    """打印消息"""
    if msg.role == "system":
        print(f"\n📢 {msg.content}")
    elif msg.role == "platform":
        name = PLATFORMS.get(msg.platform_id, {}).get("name", msg.platform_id)
        prefix = ""
        if msg.is_breakpoint:
            prefix = "💔[破防] "
        elif msg.is_betrayal:
            prefix = "⚡[叛变] "
        print(f"\n{name}: {prefix}{msg.content}")

# ==================== 入口 ====================

if __name__ == "__main__":
    import sys
    
    if "--cli" in sys.argv:
        # CLI测试模式
        asyncio.run(cli_main())
    else:
        # 启动Gradio UI
        from ui.app import create_app
        app = create_app()
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False
        )
