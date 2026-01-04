"""
情绪系统 - 管理平台情绪值和破防机制
"""
import json
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class EmotionLevel(Enum):
    """情绪等级"""
    EXCITED = "excited"      # 兴奋 80-100
    HAPPY = "happy"          # 开心 60-79
    NEUTRAL = "neutral"      # 平静 40-59
    ANNOYED = "annoyed"      # 烦躁 20-39
    ANGRY = "angry"          # 愤怒 10-19
    BROKEN = "broken"        # 破防 0-9


@dataclass
class EmotionEvent:
    """情绪事件"""
    trigger: str           # 触发内容
    delta: int            # 变化量
    source: str           # 来源 (platform_id or "user")
    event_type: str       # 事件类型


class EmotionSystem:
    """情绪管理系统"""
    
    # 情绪变化参数
    BASE_DECAY = 2                    # 每轮自然恢复
    TRIGGER_DAMAGE = 15               # 触发破防点伤害
    RIVAL_ATTACK_DAMAGE = 20          # 死对头攻击伤害
    USER_SUPPORT_HEAL = 10            # 用户支持恢复
    USER_ATTACK_DAMAGE = 25           # 用户攻击伤害（更疼）
    BREAKPOINT_THRESHOLD = 15         # 破防阈值
    RECOVERY_FROM_BREAKPOINT = 30     # 破防后恢复值
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.secrets = self._load_config("secrets.json")
        self.relationships = self._load_config("relationships.json")
        
        # 平台情绪状态
        self.emotion_states: Dict[str, int] = {}
        self.emotion_history: Dict[str, List[EmotionEvent]] = {}
        self.broken_status: Dict[str, bool] = {}
        self.broken_count: Dict[str, int] = {}
    
    def _load_config(self, filename: str) -> dict:
        """加载配置"""
        import os
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def initialize_platform(self, platform_id: str, initial_value: int = 50):
        """初始化平台情绪"""
        self.emotion_states[platform_id] = initial_value
        self.emotion_history[platform_id] = []
        self.broken_status[platform_id] = False
        self.broken_count[platform_id] = 0
    
    def get_emotion_level(self, platform_id: str) -> EmotionLevel:
        """获取当前情绪等级"""
        value = self.emotion_states.get(platform_id, 50)
        
        if self.broken_status.get(platform_id, False):
            return EmotionLevel.BROKEN
        elif value >= 80:
            return EmotionLevel.EXCITED
        elif value >= 60:
            return EmotionLevel.HAPPY
        elif value >= 40:
            return EmotionLevel.NEUTRAL
        elif value >= 20:
            return EmotionLevel.ANNOYED
        elif value >= 10:
            return EmotionLevel.ANGRY
        else:
            return EmotionLevel.BROKEN
    
    def get_emotion_emoji(self, platform_id: str) -> str:
        """获取情绪表情"""
        level = self.get_emotion_level(platform_id)
        emoji_map = {
            EmotionLevel.EXCITED: "🤩",
            EmotionLevel.HAPPY: "😊",
            EmotionLevel.NEUTRAL: "😐",
            EmotionLevel.ANNOYED: "😤",
            EmotionLevel.ANGRY: "😠",
            EmotionLevel.BROKEN: "😭💔"
        }
        return emoji_map.get(level, "😐")
    
    def check_triggers(self, platform_id: str, message: str, source: str) -> List[EmotionEvent]:
        """检查消息中的情绪触发点"""
        events = []
        platform_secrets = self.secrets.get("platform_secrets", {}).get(platform_id, {})
        
        # 检查破防触发词
        triggers = platform_secrets.get("breakpoint_triggers", [])
        for trigger in triggers:
            if trigger.lower() in message.lower():
                damage = self.TRIGGER_DAMAGE
                # 如果是用户说的，伤害加倍
                if source == "user":
                    damage = self.USER_ATTACK_DAMAGE
                # 如果是死对头说的，伤害增加
                elif self._is_rival(platform_id, source):
                    damage = self.RIVAL_ATTACK_DAMAGE
                
                events.append(EmotionEvent(
                    trigger=trigger,
                    delta=-damage,
                    source=source,
                    event_type="breakpoint_trigger"
                ))
        
        # 检查正面词汇
        happy_keywords = platform_secrets.get("vulnerability", {}).get("healing_words", [])
        for keyword in happy_keywords:
            if keyword.lower() in message.lower():
                events.append(EmotionEvent(
                    trigger=keyword,
                    delta=self.USER_SUPPORT_HEAL,
                    source=source,
                    event_type="support"
                ))
        
        return events
    
    def _is_rival(self, platform_id: str, other_id: str) -> bool:
        """检查是否是死对头关系"""
        rel = self.relationships.get("relationships", {}).get(platform_id, {}).get(other_id, {})
        return rel.get("type") == "rivalry" or rel.get("intensity", 0) > 0.7
    
    def apply_emotion_change(self, platform_id: str, delta: int, 
                             source: str, reason: str = "") -> Tuple[int, bool]:
        """
        应用情绪变化
        返回: (新情绪值, 是否破防)
        """
        old_value = self.emotion_states.get(platform_id, 50)
        new_value = max(0, min(100, old_value + delta))
        self.emotion_states[platform_id] = new_value
        
        # 记录事件
        self.emotion_history[platform_id].append(EmotionEvent(
            trigger=reason,
            delta=delta,
            source=source,
            event_type="change"
        ))
        
        # 检查破防
        broke = False
        if new_value <= self.BREAKPOINT_THRESHOLD and not self.broken_status.get(platform_id, False):
            self.broken_status[platform_id] = True
            self.broken_count[platform_id] = self.broken_count.get(platform_id, 0) + 1
            broke = True
        
        return new_value, broke
    
    def process_turn(self, platform_id: str, message: str, source: str) -> dict:
        """
        处理一个对话轮次的情绪变化
        返回情绪变化报告
        """
        events = self.check_triggers(platform_id, message, source)
        
        total_delta = sum(e.delta for e in events)
        
        # 自然恢复
        if total_delta >= 0:
            total_delta += self.BASE_DECAY
        
        new_value, broke = self.apply_emotion_change(
            platform_id, total_delta, source, 
            f"来自{source}的消息"
        )
        
        return {
            "platform_id": platform_id,
            "old_value": self.emotion_states.get(platform_id, 50) - total_delta,
            "new_value": new_value,
            "delta": total_delta,
            "triggers": [e.trigger for e in events if e.delta < 0],
            "supports": [e.trigger for e in events if e.delta > 0],
            "broke": broke,
            "emotion_level": self.get_emotion_level(platform_id).value,
            "emoji": self.get_emotion_emoji(platform_id)
        }
    
    def recover_from_breakpoint(self, platform_id: str):
        """从破防状态恢复"""
        self.broken_status[platform_id] = False
        self.emotion_states[platform_id] = self.RECOVERY_FROM_BREAKPOINT
    
    def get_breakpoint_response(self, platform_id: str) -> str:
        """获取破防时的回应"""
        platform_secrets = self.secrets.get("platform_secrets", {}).get(platform_id, {})
        responses = platform_secrets.get("breakpoint_responses", [])
        
        if responses:
            return random.choice(responses)
        return "...我不想说话了。"
    
    def get_emotion_modifier(self, platform_id: str) -> dict:
        """获取情绪对说话风格的影响"""
        level = self.get_emotion_level(platform_id)
        
        modifiers = {
            EmotionLevel.EXCITED: {
                "speed_modifier": 1.3,
                "exclamation_boost": True,
                "emoji_boost": True,
                "style_hint": "非常兴奋，语速加快，多用感叹号"
            },
            EmotionLevel.HAPPY: {
                "speed_modifier": 1.1,
                "exclamation_boost": False,
                "emoji_boost": True,
                "style_hint": "心情不错，语气轻松"
            },
            EmotionLevel.NEUTRAL: {
                "speed_modifier": 1.0,
                "exclamation_boost": False,
                "emoji_boost": False,
                "style_hint": "正常状态"
            },
            EmotionLevel.ANNOYED: {
                "speed_modifier": 1.1,
                "exclamation_boost": True,
                "emoji_boost": False,
                "style_hint": "有点烦躁，语气变冲"
            },
            EmotionLevel.ANGRY: {
                "speed_modifier": 1.2,
                "exclamation_boost": True,
                "emoji_boost": False,
                "style_hint": "很生气，可能会出言不逊"
            },
            EmotionLevel.BROKEN: {
                "speed_modifier": 0.8,
                "exclamation_boost": True,
                "emoji_boost": False,
                "style_hint": "情绪崩溃，可能会说出真心话或反击"
            }
        }
        
        return modifiers.get(level, modifiers[EmotionLevel.NEUTRAL])
    
    def get_status_display(self, platform_id: str) -> str:
        """获取情绪状态显示"""
        value = self.emotion_states.get(platform_id, 50)
        emoji = self.get_emotion_emoji(platform_id)
        level = self.get_emotion_level(platform_id)
        
        # 进度条
        filled = int(value / 10)
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        
        status_text = {
            EmotionLevel.EXCITED: "嗨起来了！",
            EmotionLevel.HAPPY: "心情不错~",
            EmotionLevel.NEUTRAL: "正常营业",
            EmotionLevel.ANNOYED: "有点烦...",
            EmotionLevel.ANGRY: "快绷不住了",
            EmotionLevel.BROKEN: "💔 破防了！"
        }
        
        return f"{emoji} [{bar}] {value}/100 {status_text.get(level, '')}"


class BreakpointManager:
    """破防名场面管理"""
    
    def __init__(self, emotion_system: EmotionSystem):
        self.emotion_system = emotion_system
        self.breakpoint_moments: List[dict] = []
    
    def record_breakpoint(self, platform_id: str, trigger: str, 
                          context: List[str], response: str):
        """记录破防名场面"""
        moment = {
            "platform_id": platform_id,
            "trigger": trigger,
            "context": context[-3:],  # 最近3条消息
            "response": response,
            "timestamp": None  # 可以加时间戳
        }
        self.breakpoint_moments.append(moment)
    
    def get_highlight_reel(self) -> List[dict]:
        """获取破防名场面集锦"""
        return self.breakpoint_moments
    
    def format_highlight(self, moment: dict) -> str:
        """格式化单个破防名场面"""
        return f"""
═══════ 💔 破防名场面 💔 ═══════
触发词: "{moment['trigger']}"
上下文: 
{chr(10).join('  ' + c for c in moment['context'])}
破防回应:
  "{moment['response']}"
══════════════════════════════
"""


if __name__ == "__main__":
    # 测试情绪系统
    system = EmotionSystem()
    system.initialize_platform("douyin")
    system.initialize_platform("zhihu")
    
    print("初始状态:")
    print(f"抖音: {system.get_status_display('douyin')}")
    print(f"知乎: {system.get_status_display('zhihu')}")
    
    # 模拟知乎攻击抖音
    result = system.process_turn("douyin", "抖音用户都没内涵，典型的信息茧房受害者", "zhihu")
    print(f"\n知乎说了: '抖音用户都没内涵，典型的信息茧房受害者'")
    print(f"抖音情绪变化: {result}")
    print(f"抖音状态: {system.get_status_display('douyin')}")
    
    # 继续攻击
    for i in range(3):
        result = system.process_turn("douyin", "没文化就是没文化", "zhihu")
        print(f"\n第{i+2}轮攻击后抖音状态: {system.get_status_display('douyin')}")
        if result['broke']:
            print(f"🔥 抖音破防了！")
            print(f"破防回应: {system.get_breakpoint_response('douyin')}")
            break
