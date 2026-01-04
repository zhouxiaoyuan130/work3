"""
私聊系统 - 管理平台与用户之间的私聊（阴谋系统）
"""
import json
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import os


class PrivateMessageType(Enum):
    """私信类型"""
    ALLIANCE = "alliance"          # 联盟邀请
    GOSSIP = "gossip"              # 八卦爆料
    COMPLAINT = "complaint"        # 吐槽抱怨
    SECRET = "secret"              # 透露秘密
    BETRAYAL_HINT = "betrayal"     # 叛变暗示
    MANIPULATION = "manipulation"  # 操控请求


@dataclass
class PrivateMessage:
    """私信消息"""
    sender: str                    # 发送平台
    recipient: str                 # 接收者 (通常是 "user")
    content: str                   # 消息内容
    msg_type: PrivateMessageType   # 消息类型
    target_platform: Optional[str] = None  # 针对的平台
    options: List[str] = field(default_factory=list)  # 用户选项
    consequence: Dict = field(default_factory=dict)   # 选择后果


class PrivateMessageSystem:
    """私聊系统"""
    
    # 私信触发概率
    BASE_TRIGGER_CHANCE = 0.25          # 基础触发概率
    RIVALRY_BOOST = 0.15                # 死对头增加概率
    EMOTION_BOOST = 0.1                 # 低情绪增加概率
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.platforms_config = self._load_config("platforms.json")
        self.relationships = self._load_config("relationships.json")
        self.secrets = self._load_config("secrets.json")
        
        # 消息队列
        self.pending_messages: List[PrivateMessage] = []
        self.message_history: List[PrivateMessage] = []
        
        # 用户选择记录
        self.user_choices: List[dict] = []
        self.alliance_status: Dict[str, bool] = {}  # 用户与各平台的联盟状态
    
    def _load_config(self, filename: str) -> dict:
        """加载配置"""
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _get_platform_name(self, platform_id: str) -> str:
        """获取平台显示名称"""
        return self.platforms_config.get("platforms", {}).get(platform_id, {}).get("name", platform_id)
    
    def should_trigger_private_message(self, platform_id: str, 
                                       other_platforms: List[str],
                                       emotion_value: int,
                                       recent_conflict: bool) -> bool:
        """判断是否应该触发私信"""
        chance = self.BASE_TRIGGER_CHANCE
        
        # 死对头在场增加概率
        for other in other_platforms:
            rel = self.relationships.get("relationships", {}).get(platform_id, {}).get(other, {})
            if rel.get("type") == "rivalry" or rel.get("intensity", 0) > 0.7:
                chance += self.RIVALRY_BOOST
        
        # 低情绪增加概率
        if emotion_value < 40:
            chance += self.EMOTION_BOOST
        
        # 最近有冲突增加概率
        if recent_conflict:
            chance += 0.1
        
        return random.random() < chance
    
    def generate_private_message(self, sender_id: str, 
                                 target_platform: str,
                                 context: str = "") -> Optional[PrivateMessage]:
        """生成私信"""
        sender_name = self._get_platform_name(sender_id)
        target_name = self._get_platform_name(target_platform)
        
        # 获取关系信息
        rel = self.relationships.get("relationships", {}).get(sender_id, {}).get(target_platform, {})
        rel_type = rel.get("type", "neutral")
        attack_lines = rel.get("attack_lines", [])
        secret_respect = rel.get("secret_respect", "")
        
        # 根据关系类型选择消息类型
        if rel_type == "rivalry":
            msg_type = random.choice([PrivateMessageType.ALLIANCE, PrivateMessageType.GOSSIP])
        elif rel_type in ["mutual_respect", "sisters"]:
            msg_type = random.choice([PrivateMessageType.GOSSIP, PrivateMessageType.SECRET])
        else:
            msg_type = random.choice(list(PrivateMessageType))
        
        # 生成消息内容
        content, options = self._generate_message_content(
            sender_id, sender_name, target_platform, target_name,
            msg_type, attack_lines, secret_respect, context
        )
        
        if not content:
            return None
        
        msg = PrivateMessage(
            sender=sender_id,
            recipient="user",
            content=content,
            msg_type=msg_type,
            target_platform=target_platform,
            options=options,
            consequence=self._generate_consequences(msg_type, sender_id, target_platform)
        )
        
        self.pending_messages.append(msg)
        return msg
    
    def _generate_message_content(self, sender_id: str, sender_name: str,
                                  target_id: str, target_name: str,
                                  msg_type: PrivateMessageType,
                                  attack_lines: List[str],
                                  secret_respect: str,
                                  context: str) -> Tuple[str, List[str]]:
        """生成消息内容和选项"""
        
        templates = {
            PrivateMessageType.ALLIANCE: {
                "content": [
                    f"悄悄@你：你看{target_name}那个发言，典型的xxx，我们要不要联合起来针对ta？",
                    f"私聊你：{target_name}今天是不是有点过分了？我觉得我们应该团结一下...",
                    f"小声说：那边说的话你信？{random.choice(attack_lines) if attack_lines else '也太那啥了'}",
                ],
                "options": [
                    "同意联盟，一起针对ta",
                    "保持中立，两不相帮",
                    "把这条私信截图发到群里"
                ]
            },
            PrivateMessageType.GOSSIP: {
                "content": [
                    f"偷偷告诉你：其实{target_name}私下里{secret_respect if secret_respect else '也没那么自信'}",
                    f"你知道吗？{target_name}最怕别人说ta{self._get_fear(target_id)}",
                    f"八卦一下：{target_name}之前被全网嘲过{self._get_public_shame(target_id)}",
                ],
                "options": [
                    "有意思，记下了",
                    "别在背后说人坏话",
                    "直接在群里问ta是不是真的"
                ]
            },
            PrivateMessageType.COMPLAINT: {
                "content": [
                    f"呜呜呜{target_name}刚才说的话好伤人...",
                    f"你有没有觉得{target_name}今天针对我？",
                    f"我是不是说错什么了？为什么{target_name}一直怼我...",
                ],
                "options": [
                    "安慰ta",
                    "确实，ta有点过分",
                    "你自己也有问题吧"
                ]
            },
            PrivateMessageType.SECRET: {
                "content": [
                    f"其实我有个秘密...{self._get_private_shame(sender_id)}",
                    f"别跟别人说，{target_name}其实私下{secret_respect if secret_respect else '也挺努力的'}",
                    f"实话跟你说，我有时候也觉得{self._get_self_doubt(sender_id)}",
                ],
                "options": [
                    "谢谢你的信任",
                    "这个秘密我会保守的",
                    "等等，让我截个图..."
                ]
            },
            PrivateMessageType.BETRAYAL_HINT: {
                "content": [
                    f"说实话，关于刚才的话题...我其实{self._get_betrayal_hint(sender_id)}",
                    f"你别告诉{target_name}，但我觉得ta说的有些道理...",
                    f"虽然我嘴上不承认，但{self._get_secret_agreement(sender_id, target_id)}",
                ],
                "options": [
                    "理解，每个人都有复杂的一面",
                    "哦？继续说",
                    "有意思，我去告诉ta"
                ]
            },
            PrivateMessageType.MANIPULATION: {
                "content": [
                    f"你能不能帮我问一下{target_name}是不是对我有意见？",
                    f"下次{target_name}再说那种话，你帮我怼回去呗？",
                    f"我觉得你比较公正，能不能帮我评评理？",
                ],
                "options": [
                    "好的，我帮你",
                    "你们的事我不想掺和",
                    "你自己去说啊，别拉我下水"
                ]
            }
        }
        
        template = templates.get(msg_type, templates[PrivateMessageType.GOSSIP])
        content = random.choice(template["content"])
        options = template["options"]
        
        return content, options
    
    def _get_fear(self, platform_id: str) -> str:
        """获取平台的恐惧"""
        secrets = self.secrets.get("platform_secrets", {}).get(platform_id, {})
        vulnerability = secrets.get("vulnerability", {})
        return vulnerability.get("core_fear", "xxx")[:30] + "..."
    
    def _get_public_shame(self, platform_id: str) -> str:
        """获取公开黑历史"""
        secrets = self.secrets.get("platform_secrets", {}).get(platform_id, {})
        shames = secrets.get("public_shame", [])
        return random.choice(shames) if shames else "的事"
    
    def _get_private_shame(self, platform_id: str) -> str:
        """获取私密黑历史"""
        secrets = self.secrets.get("platform_secrets", {}).get(platform_id, {})
        shames = secrets.get("private_shame", [])
        return random.choice(shames) if shames else "有些事不太想提"
    
    def _get_self_doubt(self, platform_id: str) -> str:
        """获取自我怀疑"""
        secrets = self.secrets.get("platform_secrets", {}).get(platform_id, {})
        vulnerability = secrets.get("vulnerability", {})
        return vulnerability.get("core_fear", "我是不是做错了什么")
    
    def _get_betrayal_hint(self, platform_id: str) -> str:
        """获取叛变暗示"""
        triggers = self.secrets.get("betrayal_triggers", {}).get(platform_id, {})
        return triggers.get("betrayal_statement", "也不是完全不同意对方的看法")
    
    def _get_secret_agreement(self, sender_id: str, target_id: str) -> str:
        """获取秘密认同"""
        rel = self.relationships.get("relationships", {}).get(sender_id, {}).get(target_id, {})
        return rel.get("secret_respect", "ta说的有些地方还是有道理的")
    
    def _generate_consequences(self, msg_type: PrivateMessageType,
                              sender_id: str, target_id: str) -> dict:
        """生成选择后果"""
        return {
            0: {  # 第一个选项（通常是配合）
                "sender_emotion": +10,
                "sender_relation": +5,
                "target_emotion": -5,
                "description": f"你选择站在{self._get_platform_name(sender_id)}这边"
            },
            1: {  # 第二个选项（通常是中立）
                "sender_emotion": 0,
                "sender_relation": 0,
                "target_emotion": 0,
                "description": "你保持中立"
            },
            2: {  # 第三个选项（通常是背叛/公开）
                "sender_emotion": -20,
                "sender_relation": -15,
                "target_emotion": +5,
                "description": "你选择了一个危险的选项..."
            }
        }
    
    def process_user_choice(self, message: PrivateMessage, choice_index: int) -> dict:
        """处理用户的选择"""
        consequence = message.consequence.get(choice_index, {})
        
        result = {
            "choice": message.options[choice_index] if choice_index < len(message.options) else "",
            "consequence": consequence,
            "exposed": choice_index == 2,  # 第三个选项通常是公开
            "alliance_formed": choice_index == 0 and message.msg_type == PrivateMessageType.ALLIANCE
        }
        
        # 记录选择
        self.user_choices.append({
            "message": message,
            "choice": choice_index,
            "result": result
        })
        
        # 更新联盟状态
        if result["alliance_formed"]:
            self.alliance_status[message.sender] = True
        
        # 移出待处理队列
        if message in self.pending_messages:
            self.pending_messages.remove(message)
        
        self.message_history.append(message)
        
        return result
    
    def format_private_message(self, message: PrivateMessage) -> str:
        """格式化私信显示"""
        sender_name = self._get_platform_name(message.sender)
        
        output = f"""
╔══════════════════════════════════════╗
  🔒 来自 {sender_name} 的私信
╠══════════════════════════════════════╣
  
  {message.content}
  
╠══════════════════════════════════════╣
  你的选择:
"""
        for i, option in enumerate(message.options):
            output += f"  [{i+1}] {option}\n"
        
        output += "╚══════════════════════════════════════╝"
        
        return output
    
    def get_exposed_message_for_group(self, message: PrivateMessage) -> str:
        """生成公开到群里的消息"""
        sender_name = self._get_platform_name(message.sender)
        target_name = self._get_platform_name(message.target_platform) if message.target_platform else "某人"
        
        return f"""
🚨 【截图警告】用户把私聊截图发到群里了！

{sender_name}的私信内容：
「{message.content}」

看来{sender_name}背后有话想说呢...
"""
    
    def get_alliance_summary(self) -> str:
        """获取联盟状态总结"""
        allies = [self._get_platform_name(p) for p, allied in self.alliance_status.items() if allied]
        if allies:
            return f"你目前与以下平台结盟: {', '.join(allies)}"
        return "你目前没有与任何平台结盟"
    
    def get_betrayal_count(self) -> int:
        """获取被背叛/背叛别人的次数"""
        return sum(1 for choice in self.user_choices if choice.get("result", {}).get("exposed"))


class ConversationDrama:
    """对话剧情管理 - 管理私信引发的群聊戏剧性"""
    
    def __init__(self, private_system: PrivateMessageSystem):
        self.private_system = private_system
        self.drama_events: List[dict] = []
    
    def check_for_drama(self, recent_messages: List[dict]) -> Optional[dict]:
        """检查是否有戏剧性事件发生"""
        # 检查用户的选择是否引发了戏剧性后果
        for choice in self.private_system.user_choices[-3:]:  # 最近3个选择
            if choice.get("result", {}).get("exposed"):
                return {
                    "type": "exposure",
                    "description": "私信被公开！",
                    "affected_platforms": [choice["message"].sender, choice["message"].target_platform]
                }
        
        return None
    
    def generate_drama_response(self, platform_id: str, drama_event: dict) -> str:
        """生成平台对戏剧性事件的反应"""
        if drama_event["type"] == "exposure":
            if platform_id == drama_event["affected_platforms"][0]:
                # 被曝光者的反应
                responses = [
                    "你...你怎么能把私聊发出来！",
                    "我只是随便说说！你这样很过分！",
                    "好啊，撕破脸是吧？那我也没什么不能说的了！"
                ]
            else:
                # 被议论者的反应
                responses = [
                    "原来你背后是这么说我的？",
                    "呵，早就知道你们在背后嚼舌根",
                    "有什么话不能当面说？"
                ]
            return random.choice(responses)
        
        return ""


if __name__ == "__main__":
    # 测试私聊系统
    system = PrivateMessageSystem()
    
    # 模拟生成私信
    msg = system.generate_private_message("douyin", "zhihu", "讨论内容深度问题")
    
    if msg:
        print(system.format_private_message(msg))
        
        # 模拟用户选择
        result = system.process_user_choice(msg, 2)  # 选择公开
        print(f"\n选择结果: {result}")
        
        if result["exposed"]:
            print("\n" + system.get_exposed_message_for_group(msg))
