"""
灵魂纯度测试 - 分析用户的平台人格组成
"""
import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import Counter
import os


@dataclass
class SoulComponent:
    """灵魂成分"""
    platform_id: str
    platform_name: str
    percentage: float
    traits: List[str]
    description: str


@dataclass
class SoulAnalysisResult:
    """灵魂分析结果"""
    components: List[SoulComponent]
    dominant_platform: str
    soul_type: str
    special_traits: List[str]
    roast: str  # 毒舌点评
    advice: str  # 建议


class SoulPurityTest:
    """灵魂纯度测试系统"""
    
    # 各平台的关键词库（用于分析用户发言风格）
    PLATFORM_KEYWORDS = {
        "douyin": {
            "high_weight": ["绝了", "家人们", "DNA动了", "笑不活了", "一整个", "真的会谢", "破防", "离谱", "绝绝子"],
            "medium_weight": ["哈哈哈", "啊", "吧", "了了", "!", "！", "?", "？"],
            "low_weight": ["好", "不错", "可以"],
            "sentence_patterns": [
                r"^.{0,10}[!！]{2,}",  # 短句+多感叹号
                r"哈{3,}",  # 多个哈
                r"啊{2,}"   # 多个啊
            ]
        },
        "zhihu": {
            "high_weight": ["谢邀", "先问是不是", "简单来说", "私以为", "恕我直言", "利益相关", "以上", "其实"],
            "medium_weight": ["因此", "所以", "换句话说", "本质上", "从xx角度", "值得注意"],
            "low_weight": ["分析", "逻辑", "观点", "思考"],
            "sentence_patterns": [
                r"第[一二三四五六七八九十]",  # 分点论述
                r"首先.+其次.+最后",  # 逻辑结构
                r".{50,}"  # 长句
            ]
        },
        "xiaohongshu": {
            "high_weight": ["姐妹", "绝绝子", "氛围感", "码住", "种草", "蹲", "本xx人", "也太", "真的绝了"],
            "medium_weight": ["好看", "精致", "推荐", "分享", "✨", "💕", "💗", "🌟"],
            "low_weight": ["生活", "方式", "审美"],
            "sentence_patterns": [
                r"[✨💕💗🌟]{2,}",  # 多emoji
                r"！{2,}",  # 多感叹号
                r"也太.+了吧"  # 小红书句式
            ]
        },
        "weibo": {
            "high_weight": ["#", "热搜", "吃瓜", "啊啊啊", "救命", "姐姐", "哥哥", "冲", "破防", "转发"],
            "medium_weight": ["热", "爆", "瓜", "追", "饭"],
            "low_weight": ["明星", "八卦", "热点"],
            "sentence_patterns": [
                r"#.+#",  # 话题标签
                r"啊{3,}",  # 多个啊
                r"[！!]{3,}"  # 多感叹号
            ]
        },
        "x_twitter": {
            "high_weight": ["based", "literally", "interesting", "perspective", "thread", "RT", "take"],
            "medium_weight": ["信息", "国际", "视野", "think", "opinion", "view"],
            "low_weight": ["外媒", "报道", "新闻"],
            "sentence_patterns": [
                r"[a-zA-Z]{4,}",  # 英文单词
                r"从.+来说",  # 分析句式
                r".+角度"  # 角度句式
            ]
        },
        "tieba": {
            "high_weight": ["乐", "典", "急了", "蚌埠住", "绷不住", "鉴定为", "什么档次", "我超", "老哥", "吧友"],
            "medium_weight": ["6", "牛", "整活", "抽象", "怀旧"],
            "low_weight": ["网", "帖", "回复"],
            "sentence_patterns": [
                r"^.{0,5}$",  # 超短回复
                r"[乐典急]{1,}$",  # 结尾用梗
                r"什么档次"  # 贴吧句式
            ]
        }
    }
    
    # 灵魂类型定义
    SOUL_TYPES = {
        "pure_entertainer": {
            "condition": lambda scores: scores.get("douyin", 0) > 50,
            "name": "纯粹的快乐小丑",
            "description": "你的灵魂追求简单直接的快乐，不需要深度，只需要多巴胺"
        },
        "intellectual_pretender": {
            "condition": lambda scores: scores.get("zhihu", 0) > 50,
            "name": "知识分子（自认为）",
            "description": "你喜欢显得有深度，虽然有时候只是看起来有深度"
        },
        "aesthetic_slave": {
            "condition": lambda scores: scores.get("xiaohongshu", 0) > 50,
            "name": "审美奴隶",
            "description": "你被精致生活绑架了，但这不一定是坏事"
        },
        "drama_lover": {
            "condition": lambda scores: scores.get("weibo", 0) > 50,
            "name": "吃瓜群众本瓜",
            "description": "没有热搜你会死，承认吧"
        },
        "global_citizen": {
            "condition": lambda scores: scores.get("x_twitter", 0) > 50,
            "name": "精神国际人",
            "description": "你的视野很广，但可能脚不太沾地"
        },
        "internet_fossil": {
            "condition": lambda scores: scores.get("tieba", 0) > 50,
            "name": "互联网活化石",
            "description": "你是真正的老网民，梗是从你这传出去的"
        },
        "balanced_soul": {
            "condition": lambda scores: max(scores.values()) - min(scores.values()) < 20,
            "name": "平衡的灵魂",
            "description": "你是一个复杂的人，各种平台的毒都沾了一点"
        },
        "chaos_agent": {
            "condition": lambda scores: len([s for s in scores.values() if s > 20]) >= 4,
            "name": "混沌特工",
            "description": "你的灵魂是一锅大杂烩，各种风格随机切换"
        }
    }
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.platforms_config = self._load_config("platforms.json")
        
        # 用户发言记录
        self.user_messages: List[str] = []
        
        # 分数记录
        self.platform_scores: Dict[str, float] = {
            "douyin": 0, "zhihu": 0, "xiaohongshu": 0,
            "weibo": 0, "x_twitter": 0, "tieba": 0
        }
        
        # 行为记录
        self.behavior_log: List[dict] = []
    
    def _load_config(self, filename: str) -> dict:
        """加载配置"""
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def analyze_message(self, message: str) -> Dict[str, float]:
        """分析单条消息的平台风格占比"""
        scores = {}
        
        for platform_id, keywords in self.PLATFORM_KEYWORDS.items():
            score = 0
            
            # 高权重关键词
            for kw in keywords.get("high_weight", []):
                if kw.lower() in message.lower():
                    score += 3
            
            # 中权重关键词
            for kw in keywords.get("medium_weight", []):
                if kw.lower() in message.lower():
                    score += 1.5
            
            # 低权重关键词
            for kw in keywords.get("low_weight", []):
                if kw.lower() in message.lower():
                    score += 0.5
            
            # 句式匹配
            for pattern in keywords.get("sentence_patterns", []):
                if re.search(pattern, message):
                    score += 2
            
            scores[platform_id] = score
        
        return scores
    
    def record_message(self, message: str):
        """记录用户消息"""
        self.user_messages.append(message)
        
        # 分析并累加分数
        scores = self.analyze_message(message)
        for platform_id, score in scores.items():
            self.platform_scores[platform_id] += score
    
    def record_behavior(self, behavior_type: str, details: dict):
        """记录用户行为（如私信选择、站队等）"""
        self.behavior_log.append({
            "type": behavior_type,
            "details": details
        })
        
        # 根据行为调整分数
        self._adjust_scores_by_behavior(behavior_type, details)
    
    def _adjust_scores_by_behavior(self, behavior_type: str, details: dict):
        """根据行为调整分数"""
        adjustments = {
            "alliance_with": {  # 与某平台结盟
                "target_boost": 10,
                "rival_penalty": -5
            },
            "expose_private": {  # 公开私信
                "weibo_boost": 5,  # 爆料行为
                "zhihu_penalty": -3
            },
            "stay_neutral": {  # 保持中立
                "zhihu_boost": 3,
                "x_twitter_boost": 3
            },
            "support_broken": {  # 支持破防的一方
                "xiaohongshu_boost": 3  # 共情行为
            },
            "attack_broken": {  # 攻击破防的一方
                "tieba_boost": 5  # 抽象行为
            }
        }
        
        adj = adjustments.get(behavior_type, {})
        for key, value in adj.items():
            if "boost" in key:
                platform = key.replace("_boost", "")
                if platform in self.platform_scores:
                    self.platform_scores[platform] += value
            elif "penalty" in key:
                platform = key.replace("_penalty", "")
                if platform in self.platform_scores:
                    self.platform_scores[platform] += value  # value is negative
    
    def calculate_final_scores(self) -> Dict[str, float]:
        """计算最终百分比"""
        total = sum(self.platform_scores.values())
        if total == 0:
            # 没有数据时平均分配
            return {p: 16.67 for p in self.platform_scores}
        
        return {
            platform: round((score / total) * 100, 1)
            for platform, score in self.platform_scores.items()
        }
    
    def generate_analysis(self) -> SoulAnalysisResult:
        """生成完整的灵魂分析"""
        percentages = self.calculate_final_scores()
        
        # 按百分比排序
        sorted_platforms = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
        
        # 生成成分列表（只显示>5%的）
        components = []
        for platform_id, percentage in sorted_platforms:
            if percentage < 5:
                continue
            
            platform = self.platforms_config.get("platforms", {}).get(platform_id, {})
            component = SoulComponent(
                platform_id=platform_id,
                platform_name=platform.get("name", platform_id),
                percentage=percentage,
                traits=platform.get("personality", {}).get("traits", [])[:3],
                description=self._get_component_description(platform_id, percentage)
            )
            components.append(component)
        
        # 确定主导平台
        dominant_platform = sorted_platforms[0][0]
        
        # 确定灵魂类型
        soul_type = self._determine_soul_type(percentages)
        
        # 生成特殊特质
        special_traits = self._generate_special_traits(percentages, self.behavior_log)
        
        # 生成毒舌点评
        roast = self._generate_roast(percentages, dominant_platform)
        
        # 生成建议
        advice = self._generate_advice(percentages)
        
        return SoulAnalysisResult(
            components=components,
            dominant_platform=dominant_platform,
            soul_type=soul_type,
            special_traits=special_traits,
            roast=roast,
            advice=advice
        )
    
    def _get_component_description(self, platform_id: str, percentage: float) -> str:
        """获取成分描述"""
        descriptions = {
            "douyin": {
                "high": "你的快乐基因非常强大",
                "medium": "偶尔需要一点轻松的内容",
                "low": "你对娱乐保持警惕"
            },
            "zhihu": {
                "high": "你有强烈的表达欲和分析欲",
                "medium": "你有时候会想深入了解事物",
                "low": "你对长篇大论不太感冒"
            },
            "xiaohongshu": {
                "high": "你对生活品质有追求",
                "medium": "你欣赏美好的事物",
                "low": "你对精致生活免疫"
            },
            "weibo": {
                "high": "你是信息的狂热追踪者",
                "medium": "你关注热点但保持距离",
                "low": "你对热搜无感"
            },
            "x_twitter": {
                "high": "你渴望更广阔的视野",
                "medium": "你偶尔看看外面的世界",
                "low": "你扎根本土"
            },
            "tieba": {
                "high": "你是互联网原住民",
                "medium": "你懂一些老梗",
                "low": "你是互联网新人"
            }
        }
        
        level = "high" if percentage > 30 else "medium" if percentage > 15 else "low"
        return descriptions.get(platform_id, {}).get(level, "你与这个平台有一些联系")
    
    def _determine_soul_type(self, percentages: Dict[str, float]) -> str:
        """确定灵魂类型"""
        for type_id, type_info in self.SOUL_TYPES.items():
            if type_info["condition"](percentages):
                return type_info["name"]
        
        return "未分类的复杂灵魂"
    
    def _generate_special_traits(self, percentages: Dict[str, float], 
                                  behaviors: List[dict]) -> List[str]:
        """生成特殊特质"""
        traits = []
        
        # 基于分数的特质
        if percentages.get("douyin", 0) > 30 and percentages.get("zhihu", 0) > 20:
            traits.append("🎭 双面人：既要快乐也要深度")
        
        if percentages.get("xiaohongshu", 0) > 25 and percentages.get("tieba", 0) > 15:
            traits.append("⚡ 反差萌：精致与抽象并存")
        
        if percentages.get("weibo", 0) > 30:
            traits.append("🍉 吃瓜体质：八卦雷达永远在线")
        
        # 基于行为的特质
        expose_count = sum(1 for b in behaviors if b["type"] == "expose_private")
        if expose_count > 0:
            traits.append("📢 大嘴巴：保不住秘密")
        
        neutral_count = sum(1 for b in behaviors if b["type"] == "stay_neutral")
        if neutral_count >= 2:
            traits.append("🧘 老滑头：从不站队")
        
        return traits[:5]  # 最多5个特质
    
    def _generate_roast(self, percentages: Dict[str, float], 
                        dominant: str) -> str:
        """生成毒舌点评"""
        roasts = {
            "douyin": "你的注意力可能撑不过15秒，但没关系，快乐最重要对吧？",
            "zhihu": "谢邀，你的灵魂里住着一个急于表达的中年男人，不管别人问没问。",
            "xiaohongshu": "你的生活可能没有那么精致，但你的朋友圈一定有。",
            "weibo": "没有热搜的日子你不知道该关心什么，对吗？",
            "x_twitter": "你转发了那么多英文推文，确定都看懂了吗？",
            "tieba": "你嘴上说着'乐'，但内心深处藏着对互联网黄金时代的怀念。"
        }
        
        return roasts.get(dominant, "你是一个复杂的人，我无法简单地吐槽你。")
    
    def _generate_advice(self, percentages: Dict[str, float]) -> str:
        """生成建议"""
        dominant = max(percentages, key=percentages.get)
        
        advices = {
            "douyin": "试着偶尔看一些长文章，你的大脑会感谢你的。",
            "zhihu": "有时候不需要分析，享受当下也很好。",
            "xiaohongshu": "记住：滤镜后面的生活才是真实的。",
            "weibo": "热搜会过去的，找到自己真正关心的事情。",
            "x_twitter": "多了解一下身边发生的事，接地气一点。",
            "tieba": "新东西也有新东西的好，不要只活在回忆里。"
        }
        
        return advices.get(dominant, "保持平衡，保持好奇。")
    
    def format_result(self, result: SoulAnalysisResult) -> str:
        """格式化输出结果"""
        output = """
╔═══════════════════════════════════════════════════════╗
           🔮 灵 魂 纯 度 测 试 结 果 🔮
╚═══════════════════════════════════════════════════════╝

📊 你的灵魂由以下成分炼成:

"""
        # 成分条
        for component in result.components:
            bar_length = int(component.percentage / 5)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            output += f"  {component.platform_name:8} [{bar}] {component.percentage}%\n"
            output += f"           {component.description}\n\n"
        
        output += f"""
═══════════════════════════════════════════════════════

🏷️ 你的灵魂类型: 【{result.soul_type}】

✨ 特殊特质:
"""
        for trait in result.special_traits:
            output += f"  • {trait}\n"
        
        output += f"""
═══════════════════════════════════════════════════════

😈 毒舌点评:
  "{result.roast}"

💡 给你的建议:
  "{result.advice}"

═══════════════════════════════════════════════════════
"""
        return output
    
    def get_quick_summary(self) -> str:
        """获取快速总结（一句话版本）"""
        percentages = self.calculate_final_scores()
        sorted_platforms = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
        
        # 取前三
        top_3 = sorted_platforms[:3]
        parts = []
        for platform_id, percentage in top_3:
            platform = self.platforms_config.get("platforms", {}).get(platform_id, {})
            name = platform.get("name", platform_id)
            parts.append(f"{int(percentage)}%{name}")
        
        return f"你的灵魂由 {' + '.join(parts)} 炼成"


if __name__ == "__main__":
    # 测试灵魂纯度测试
    test = SoulPurityTest()
    
    # 模拟用户发言
    messages = [
        "家人们谁懂啊，这也太绝了！",
        "我觉得这个问题可以从几个角度来分析...",
        "姐妹们码住！这个氛围感绝绝子✨",
        "热搜又爆了啊啊啊啊！",
        "乐，典中典了属于是",
        "从国际视角来看，这个perspective很interesting"
    ]
    
    for msg in messages:
        test.record_message(msg)
    
    # 模拟一些行为
    test.record_behavior("expose_private", {"target": "zhihu"})
    test.record_behavior("alliance_with", {"target": "douyin"})
    
    # 生成分析
    result = test.generate_analysis()
    print(test.format_result(result))
    print("\n快速总结:", test.get_quick_summary())
