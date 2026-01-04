"""
核心对话引擎 - 管理多平台AI群聊
"""
import json
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import os


class MessageType(Enum):
    """消息类型"""
    PUBLIC = "public"          # 群聊消息
    PRIVATE = "private"        # 私聊消息
    SYSTEM = "system"          # 系统消息
    BREAKPOINT = "breakpoint"  # 破防消息


@dataclass
class Message:
    """消息数据结构"""
    sender: str              # 发送者 (平台名 or "user")
    content: str             # 消息内容
    msg_type: MessageType    # 消息类型
    target: Optional[str] = None  # 私聊目标
    emotion_delta: int = 0   # 情绪变化量
    is_multi_part: bool = False  # 是否分条发送
    parts: List[str] = field(default_factory=list)  # 分条内容


@dataclass 
class PlatformState:
    """平台状态"""
    name: str
    emotion_value: int = 50       # 情绪值 0-100
    is_broken: bool = False       # 是否破防
    betrayal_count: int = 0       # 叛变次数
    relationship_with_user: int = 50  # 与用户关系 0-100
    private_opinion_of_user: str = ""  # 对用户的私下评价
    soul_influence: float = 0.0   # 对用户灵魂的影响比例


class ChatEngine:
    """核心对话引擎"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.platforms_config = self._load_config("platforms.json")
        self.relationships = self._load_config("relationships.json")
        self.topics = self._load_config("topics.json")
        self.secrets = self._load_config("secrets.json")
        
        # 当前会话状态
        self.active_platforms: Dict[str, PlatformState] = {}
        self.chat_history: List[Message] = []
        self.current_topic: Optional[dict] = None
        self.turn_count: int = 0
        
        # 用户分析
        self.user_word_analysis: Dict[str, int] = {}  # 用户词汇分析
        self.user_style_scores: Dict[str, float] = {
            "douyin": 0, "zhihu": 0, "xiaohongshu": 0,
            "weibo": 0, "x_twitter": 0, "tieba": 0
        }
    
    def _load_config(self, filename: str) -> dict:
        """加载配置文件"""
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告: 配置文件 {filename} 不存在")
            return {}
    
    def start_session(self, platform1: str, platform2: str) -> str:
        """开始一个新会话"""
        # 初始化平台状态
        self.active_platforms = {
            platform1: PlatformState(name=platform1),
            platform2: PlatformState(name=platform2)
        }
        self.chat_history = []
        self.turn_count = 0
        
        # 生成开场白
        intro = self._generate_intro(platform1, platform2)
        return intro
    
    def _generate_intro(self, p1: str, p2: str) -> str:
        """生成开场介绍"""
        p1_name = self.platforms_config["platforms"][p1]["name"]
        p2_name = self.platforms_config["platforms"][p2]["name"]
        p1_avatar = self.platforms_config["platforms"][p1]["avatar"]
        p2_avatar = self.platforms_config["platforms"][p2]["avatar"]
        
        # 获取关系描述
        rel = self.relationships["relationships"].get(p1, {}).get(p2, {})
        rel_type = rel.get("type", "neutral")
        rel_desc = rel.get("description", "关系一般")
        
        intro = f"""
╔══════════════════════════════════════╗
  🎭 平台人格群聊已开启
  
  参与者:
  {p1_avatar} {p1_name} 
  {p2_avatar} {p2_name}
  👤 你
  
  他们的关系: {rel_type}
  {rel_desc}
╚══════════════════════════════════════╝
"""
        return intro
    
    def get_random_topics(self, count: int = 3) -> List[dict]:
        """获取随机话题"""
        all_topics = []
        categories = self.topics.get("topic_categories", {})
        weights = self.topics.get("random_topic_settings", {}).get("category_weights", {})
        
        for cat_name, cat_data in categories.items():
            cat_weight = weights.get(cat_name, 0.2)
            for topic in cat_data.get("topics", []):
                topic["category"] = cat_name
                topic["weight"] = cat_weight
                all_topics.append(topic)
        
        # 按权重随机选择
        selected = random.choices(all_topics, 
                                  weights=[t["weight"] for t in all_topics],
                                  k=min(count, len(all_topics)))
        return selected
    
    def select_topic(self, topic: dict):
        """选择话题"""
        self.current_topic = topic
    
    def build_platform_prompt(self, platform_id: str, context: str = "") -> str:
        """构建平台的系统提示词"""
        platform = self.platforms_config["platforms"].get(platform_id, {})
        template = self.platforms_config.get("system_prompt_template", "")
        
        # 获取其他平台信息
        other_platforms = [p for p in self.active_platforms.keys() if p != platform_id]
        other_names = [self.platforms_config["platforms"][p]["name"] for p in other_platforms]
        
        # 获取关系信息
        relationships_desc = []
        for other_id in other_platforms:
            rel = self.relationships["relationships"].get(platform_id, {}).get(other_id, {})
            relationships_desc.append(f"对{self.platforms_config['platforms'][other_id]['name']}: {rel.get('description', '一般')}")
        
        prompt = template.format(
            platform_name=platform.get("name", ""),
            core_identity=platform.get("core_identity", ""),
            mbti=platform.get("personality", {}).get("mbti", ""),
            traits=", ".join(platform.get("personality", {}).get("traits", [])),
            values=", ".join(platform.get("personality", {}).get("values", [])),
            insecurities=", ".join(platform.get("personality", {}).get("insecurities", [])),
            patterns=", ".join(platform.get("speech_style", {}).get("patterns", [])[:5]),
            quirks=", ".join(platform.get("speech_style", {}).get("quirks", [])),
            origin=platform.get("backstory", {}).get("origin", ""),
            trauma=platform.get("backstory", {}).get("trauma", ""),
            pride=platform.get("backstory", {}).get("pride", ""),
            regret=platform.get("backstory", {}).get("regret", ""),
            secret_shame=platform.get("secret_shame", ""),
            other_platforms=", ".join(other_names),
            relationships="; ".join(relationships_desc)
        )
        
        # 添加当前情绪状态
        state = self.active_platforms.get(platform_id)
        if state:
            prompt += f"\n\n【当前状态】\n情绪值: {state.emotion_value}/100"
            if state.emotion_value < 30:
                prompt += "\n⚠️ 情绪低落，容易被激怒"
            if state.is_broken:
                prompt += "\n💔 已破防，情绪失控中"
        
        # 添加上下文
        if context:
            prompt += f"\n\n【当前话题】\n{context}"
        
        return prompt
    
    def analyze_user_message(self, message: str) -> Dict[str, float]:
        """分析用户消息，计算各平台风格占比"""
        style_keywords = {
            "douyin": ["绝了", "家人们", "DNA", "笑死", "破防", "哈哈哈", "啊？", "离谱", "绝绝子"],
            "zhihu": ["其实", "所以", "因此", "换句话说", "简单来说", "值得注意", "从xx角度", "本质上"],
            "xiaohongshu": ["姐妹", "真的绝了", "码住", "种草", "氛围感", "✨", "💕", "好好看"],
            "weibo": ["#", "热搜", "吃瓜", "啊啊啊", "救命", "姐姐", "哥哥", "冲"],
            "x_twitter": ["literally", "based", "interesting", "perspective", "thread", "RT"],
            "tieba": ["乐", "典", "急了", "蚌埠住", "绷不住", "鉴定为", "什么档次", "老哥"]
        }
        
        scores = {}
        total = 0
        for platform, keywords in style_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in message.lower())
            scores[platform] = score
            total += score
        
        # 归一化
        if total > 0:
            for platform in scores:
                scores[platform] /= total
                self.user_style_scores[platform] += scores[platform]
        
        return scores
    
    def check_emotion_triggers(self, platform_id: str, message: str) -> Tuple[int, bool]:
        """检查消息是否触发情绪变化"""
        secrets = self.secrets.get("platform_secrets", {}).get(platform_id, {})
        triggers = secrets.get("breakpoint_triggers", [])
        
        emotion_delta = 0
        triggered = False
        
        for trigger in triggers:
            if trigger.lower() in message.lower():
                emotion_delta -= 15
                triggered = True
        
        return emotion_delta, triggered
    
    def check_betrayal(self, platform_id: str, topic_content: str) -> Optional[str]:
        """检查是否触发叛变"""
        betrayal_config = self.secrets.get("betrayal_triggers", {}).get(platform_id, {})
        keywords = betrayal_config.get("topic_keywords", [])
        probability = betrayal_config.get("betrayal_probability", 0.2)
        
        # 检查话题是否包含叛变关键词
        keyword_match = any(kw.lower() in topic_content.lower() for kw in keywords)
        
        if keyword_match and random.random() < probability:
            return betrayal_config.get("betrayal_statement", "")
        
        return None
    
    def generate_private_message(self, from_platform: str, target: str = "user") -> Optional[Message]:
        """生成私聊消息（阴谋邀请）"""
        if random.random() > 0.3:  # 30%概率触发私聊
            return None
        
        other_platforms = [p for p in self.active_platforms.keys() if p != from_platform]
        if not other_platforms:
            return None
        
        target_platform = random.choice(other_platforms)
        target_name = self.platforms_config["platforms"][target_platform]["name"]
        from_name = self.platforms_config["platforms"][from_platform]["name"]
        
        # 获取攻击话术
        rel = self.relationships["relationships"].get(from_platform, {}).get(target_platform, {})
        attack_lines = rel.get("attack_lines", ["那边说的话你信？"])
        
        templates = [
            f"悄悄@你：你看{target_name}那个发言，典型的xxx，我们要不要联合起来...",
            f"私聊你：{target_name}刚才那话什么意思啊？感觉在针对我们？",
            f"偷偷告诉你：其实{target_name}私下里{rel.get('secret_respect', '也没那么讨厌')}",
            f"小声bb：我觉得{target_name}今天有点反常，你发现了吗？",
        ]
        
        content = random.choice(templates)
        
        return Message(
            sender=from_platform,
            content=f"【{from_name}的私信】\n{content}",
            msg_type=MessageType.PRIVATE,
            target="user"
        )
    
    def end_session(self) -> dict:
        """结束会话，生成总结"""
        result = {
            "private_evaluations": {},
            "soul_purity_test": {},
            "chat_summary": {
                "total_turns": self.turn_count,
                "breakpoints": sum(1 for p in self.active_platforms.values() if p.is_broken),
                "betrayals": sum(p.betrayal_count for p in self.active_platforms.values())
            }
        }
        
        # 生成各平台对用户的私下评价
        for platform_id, state in self.active_platforms.items():
            platform_name = self.platforms_config["platforms"][platform_id]["name"]
            
            if state.relationship_with_user > 70:
                eval_template = "这个人还不错，{positive_trait}，下次可以多聊聊。"
            elif state.relationship_with_user > 40:
                eval_template = "一般般吧，{neutral_trait}，不功不过。"
            else:
                eval_template = "有点无语，{negative_trait}，希望下次别遇到。"
            
            result["private_evaluations"][platform_name] = eval_template
        
        # 计算灵魂纯度
        total = sum(self.user_style_scores.values())
        if total > 0:
            for platform_id, score in self.user_style_scores.items():
                platform_name = self.platforms_config["platforms"][platform_id]["name"]
                percentage = int((score / total) * 100)
                if percentage > 0:
                    result["soul_purity_test"][platform_name] = percentage
        
        return result
    
    def format_chat_history(self, last_n: int = 10) -> str:
        """格式化最近的聊天记录"""
        recent = self.chat_history[-last_n:] if len(self.chat_history) > last_n else self.chat_history
        
        formatted = []
        for msg in recent:
            if msg.msg_type == MessageType.PUBLIC:
                if msg.sender == "user":
                    formatted.append(f"👤 你: {msg.content}")
                else:
                    platform = self.platforms_config["platforms"].get(msg.sender, {})
                    avatar = platform.get("avatar", "🤖")
                    name = platform.get("name", msg.sender)
                    formatted.append(f"{avatar} {name}: {msg.content}")
            elif msg.msg_type == MessageType.PRIVATE:
                formatted.append(f"🔒 {msg.content}")
        
        return "\n".join(formatted)


def create_engine(config_dir: str = "config") -> ChatEngine:
    """工厂函数：创建对话引擎实例"""
    return ChatEngine(config_dir)


if __name__ == "__main__":
    # 测试代码
    engine = create_engine()
    
    # 测试开始会话
    intro = engine.start_session("douyin", "zhihu")
    print(intro)
    
    # 测试获取话题
    topics = engine.get_random_topics(3)
    for i, topic in enumerate(topics, 1):
        print(f"{i}. {topic['title']}")
    
    # 测试构建提示词
    prompt = engine.build_platform_prompt("douyin", "讨论深度内容vs娱乐内容")
    print("\n抖音的系统提示词片段:")
    print(prompt[:500] + "...")
