"""
叛变机制 - 管理平台的立场反转
"""
import json
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import os


@dataclass
class BetrayalEvent:
    """叛变事件"""
    platform_id: str           # 叛变的平台
    trigger_topic: str         # 触发话题
    original_stance: str       # 原本立场
    new_stance: str           # 新立场
    statement: str            # 叛变宣言
    shock_value: int          # 震惊程度 1-10


class BetrayalSystem:
    """叛变系统"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.platforms_config = self._load_config("platforms.json")
        self.secrets = self._load_config("secrets.json")
        self.relationships = self._load_config("relationships.json")
        
        # 叛变记录
        self.betrayal_history: List[BetrayalEvent] = []
        self.platform_betrayal_count: Dict[str, int] = {}
        
        # 叛变冷却（防止频繁叛变）
        self.betrayal_cooldown: Dict[str, int] = {}  # platform_id -> turns until can betray
    
    def _load_config(self, filename: str) -> dict:
        """加载配置"""
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def check_betrayal_trigger(self, platform_id: str, 
                               topic_content: str,
                               current_emotion: int) -> Optional[BetrayalEvent]:
        """
        检查是否触发叛变
        低情绪 + 特定话题 = 更容易叛变
        """
        # 检查冷却
        if self.betrayal_cooldown.get(platform_id, 0) > 0:
            return None
        
        betrayal_config = self.secrets.get("betrayal_triggers", {}).get(platform_id, {})
        keywords = betrayal_config.get("topic_keywords", [])
        base_probability = betrayal_config.get("betrayal_probability", 0.2)
        
        # 检查话题是否包含叛变关键词
        keyword_matches = [kw for kw in keywords if kw.lower() in topic_content.lower()]
        
        if not keyword_matches:
            return None
        
        # 计算实际概率
        # 低情绪增加叛变概率
        emotion_modifier = (50 - current_emotion) / 100  # 情绪越低，修正越高
        final_probability = min(0.8, base_probability + emotion_modifier * 0.3)
        
        # 多次触发同一关键词增加概率
        keyword_bonus = len(keyword_matches) * 0.1
        final_probability = min(0.9, final_probability + keyword_bonus)
        
        if random.random() > final_probability:
            return None
        
        # 触发叛变！
        event = self._create_betrayal_event(platform_id, keyword_matches[0], topic_content)
        
        if event:
            self.betrayal_history.append(event)
            self.platform_betrayal_count[platform_id] = \
                self.platform_betrayal_count.get(platform_id, 0) + 1
            self.betrayal_cooldown[platform_id] = 5  # 5轮冷却
        
        return event
    
    def _create_betrayal_event(self, platform_id: str, 
                               trigger_keyword: str,
                               context: str) -> Optional[BetrayalEvent]:
        """创建叛变事件"""
        betrayal_config = self.secrets.get("betrayal_triggers", {}).get(platform_id, {})
        statement = betrayal_config.get("betrayal_statement", "")
        
        if not statement:
            return None
        
        # 根据平台特点生成叛变细节
        platform = self.platforms_config.get("platforms", {}).get(platform_id, {})
        platform_name = platform.get("name", platform_id)
        
        # 原本立场（根据平台核心身份）
        original_stance = platform.get("core_identity", "")
        
        # 新立场（承认对立观点）
        new_stance = self._generate_new_stance(platform_id, trigger_keyword)
        
        # 计算震惊程度
        shock_value = self._calculate_shock_value(platform_id, trigger_keyword)
        
        return BetrayalEvent(
            platform_id=platform_id,
            trigger_topic=trigger_keyword,
            original_stance=original_stance[:50] + "..." if len(original_stance) > 50 else original_stance,
            new_stance=new_stance,
            statement=statement,
            shock_value=shock_value
        )
    
    def _generate_new_stance(self, platform_id: str, trigger_keyword: str) -> str:
        """生成叛变后的新立场"""
        stance_templates = {
            "douyin": {
                "青少年": "也许...算法确实应该对青少年更负责任",
                "算法危害": "说实话，有时候刷着刷着一晚上就过去了",
                "内容同质化": "确实，最近推送的内容都差不多",
                "沉迷": "我也不希望大家沉迷...快乐也要有节制"
            },
            "zhihu": {
                "编故事": "好吧，我承认热门回答里确实有很多创作成分",
                "知乎文学": "情感故事确实比专业回答更受欢迎...",
                "爹味过重": "可能有时候我说话方式确实有点...居高临下"
            },
            "xiaohongshu": {
                "滤镜": "修图这事...确实有时候修过头了",
                "虚假种草": "有些推荐确实是...合作",
                "消费主义陷阱": "买东西的快乐有时候确实只是一瞬间"
            },
            "weibo": {
                "饭圈乱象": "有些粉丝的行为我自己都看不下去...",
                "买热搜": "热搜机制...确实有改进空间",
                "网暴": "我也很内疚，有些事情处理得不好"
            },
            "x_twitter": {
                "脱离实际": "天天看外媒，可能确实有点脱离国内实际",
                "信息茧房": "虽然标榜多元，但关注的账号其实也都差不多",
                "假新闻": "外媒也不一定就是真相"
            },
            "tieba": {
                "过时": "确实...用户少了很多",
                "衰落": "移动互联网时代我确实没跟上",
                "没落": "有时候也挺怀念以前的热闹"
            }
        }
        
        platform_stances = stance_templates.get(platform_id, {})
        
        for keyword, stance in platform_stances.items():
            if keyword in trigger_keyword:
                return stance
        
        return "也许对方说的有些道理..."
    
    def _calculate_shock_value(self, platform_id: str, trigger_keyword: str) -> int:
        """计算叛变震惊程度"""
        # 基础震惊值
        base_shock = 5
        
        # 核心身份相关的叛变更震惊
        core_topics = {
            "douyin": ["流量", "算法", "娱乐"],
            "zhihu": ["知识", "专业", "深度"],
            "xiaohongshu": ["精致", "审美", "种草"],
            "weibo": ["热搜", "饭圈", "热点"],
            "x_twitter": ["国际", "视野", "言论"],
            "tieba": ["抽象", "整活", "老网民"]
        }
        
        platform_core = core_topics.get(platform_id, [])
        if any(topic in trigger_keyword for topic in platform_core):
            base_shock += 3
        
        # 第一次叛变更震惊
        if self.platform_betrayal_count.get(platform_id, 0) == 0:
            base_shock += 2
        
        return min(10, base_shock)
    
    def update_cooldowns(self):
        """更新冷却时间（每轮调用）"""
        for platform_id in list(self.betrayal_cooldown.keys()):
            if self.betrayal_cooldown[platform_id] > 0:
                self.betrayal_cooldown[platform_id] -= 1
    
    def format_betrayal_event(self, event: BetrayalEvent) -> str:
        """格式化叛变事件显示"""
        platform = self.platforms_config.get("platforms", {}).get(event.platform_id, {})
        platform_name = platform.get("name", event.platform_id)
        avatar = platform.get("avatar", "🤖")
        
        shock_bar = "⚡" * event.shock_value + "○" * (10 - event.shock_value)
        
        return f"""
╔═══════════════════════════════════════════╗
  🔄 叛变警报！{avatar} {platform_name} 立场动摇了！
╠═══════════════════════════════════════════╣
  
  触发话题: "{event.trigger_topic}"
  
  原本立场: {event.original_stance}
  
  {avatar} {platform_name}说:
  「{event.statement}」
  
  新的态度: {event.new_stance}
  
  震惊程度: [{shock_bar}] {event.shock_value}/10
  
╚═══════════════════════════════════════════╝
"""
    
    def get_betrayal_prediction(self, platform_id: str, 
                                current_emotion: int,
                                topic_keywords: List[str]) -> dict:
        """预测叛变可能性（可用于UI提示）"""
        betrayal_config = self.secrets.get("betrayal_triggers", {}).get(platform_id, {})
        trigger_keywords = betrayal_config.get("topic_keywords", [])
        base_probability = betrayal_config.get("betrayal_probability", 0.2)
        
        # 检查话题匹配
        matches = [kw for kw in trigger_keywords if any(kw.lower() in t.lower() for t in topic_keywords)]
        
        if not matches:
            return {"chance": 0, "warning": False, "hints": []}
        
        # 计算概率
        emotion_modifier = (50 - current_emotion) / 100
        chance = min(0.9, base_probability + emotion_modifier * 0.3 + len(matches) * 0.1)
        
        # 生成提示
        hints = []
        if chance > 0.5:
            hints.append(f"⚠️ {self._get_platform_name(platform_id)}似乎对这个话题很敏感...")
        if current_emotion < 30:
            hints.append(f"💔 {self._get_platform_name(platform_id)}情绪很低落，可能会说出真心话")
        
        return {
            "chance": chance,
            "warning": chance > 0.4,
            "hints": hints,
            "trigger_keywords": matches
        }
    
    def _get_platform_name(self, platform_id: str) -> str:
        """获取平台名称"""
        return self.platforms_config.get("platforms", {}).get(platform_id, {}).get("name", platform_id)
    
    def get_betrayal_summary(self) -> str:
        """获取叛变总结"""
        if not self.betrayal_history:
            return "本次对话没有人叛变，大家都坚守立场！"
        
        summary = "本次对话的叛变记录:\n"
        for event in self.betrayal_history:
            platform_name = self._get_platform_name(event.platform_id)
            summary += f"- {platform_name} 在谈到「{event.trigger_topic}」时动摇了立场\n"
        
        return summary


class StanceTracker:
    """立场追踪器 - 记录和分析平台立场变化"""
    
    def __init__(self):
        self.stance_history: Dict[str, List[dict]] = {}  # platform_id -> list of stances
    
    def record_stance(self, platform_id: str, topic: str, 
                      stance: str, confidence: float):
        """记录立场"""
        if platform_id not in self.stance_history:
            self.stance_history[platform_id] = []
        
        self.stance_history[platform_id].append({
            "topic": topic,
            "stance": stance,
            "confidence": confidence,
            "turn": len(self.stance_history[platform_id])
        })
    
    def detect_stance_shift(self, platform_id: str, 
                            new_stance: str, topic: str) -> bool:
        """检测立场是否发生变化"""
        history = self.stance_history.get(platform_id, [])
        
        # 查找同一话题的历史立场
        for record in reversed(history):
            if record["topic"] == topic:
                # 简单的立场比较（实际可以用NLP更精确）
                if record["stance"] != new_stance:
                    return True
        
        return False
    
    def get_consistency_score(self, platform_id: str) -> float:
        """获取立场一致性评分"""
        history = self.stance_history.get(platform_id, [])
        if len(history) < 2:
            return 1.0
        
        # 按话题分组，检查立场变化
        topic_stances: Dict[str, List[str]] = {}
        for record in history:
            topic = record["topic"]
            if topic not in topic_stances:
                topic_stances[topic] = []
            topic_stances[topic].append(record["stance"])
        
        # 计算变化次数
        changes = 0
        total = 0
        for topic, stances in topic_stances.items():
            for i in range(1, len(stances)):
                total += 1
                if stances[i] != stances[i-1]:
                    changes += 1
        
        if total == 0:
            return 1.0
        
        return 1.0 - (changes / total)


if __name__ == "__main__":
    # 测试叛变系统
    system = BetrayalSystem()
    
    # 模拟低情绪时讨论敏感话题
    print("测试抖音在讨论'青少年沉迷'话题时的叛变:")
    for emotion in [50, 40, 30, 20, 10]:
        event = system.check_betrayal_trigger(
            "douyin",
            "抖音算法让青少年沉迷手机，这是不负责任的",
            emotion
        )
        if event:
            print(f"情绪值{emotion}时触发叛变！")
            print(system.format_betrayal_event(event))
            break
        else:
            print(f"情绪值{emotion}时未触发叛变")
        
        # 重置冷却以便测试
        system.betrayal_cooldown.clear()
