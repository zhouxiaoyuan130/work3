"""
Fish Audio TTS 集成模块
为每个平台配置独特的语音风格
"""

import aiohttp
import asyncio
import json
import os
import hashlib
import base64
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class EmotionTone(Enum):
    """情绪语调"""
    EXCITED = "excited"      # 兴奋
    HAPPY = "happy"          # 开心
    NEUTRAL = "neutral"      # 中性
    ANNOYED = "annoyed"      # 烦躁
    ANGRY = "angry"          # 愤怒
    BROKEN = "broken"        # 破防/哭泣
    SARCASTIC = "sarcastic"  # 阴阳怪气


@dataclass
class VoiceConfig:
    """语音配置"""
    reference_id: str        # Fish Audio 参考音频ID（你的唱歌声音）
    speed: float = 1.0       # 语速 0.5-2.0
    pitch: float = 0         # 音调 -12 到 12
    energy: float = 1.0      # 能量/响度 0.5-2.0
    emotion: str = "neutral" # 情绪标签
    pause_between: float = 0.3  # 分条消息间停顿（秒）


# 各平台默认语音配置
PLATFORM_VOICE_CONFIGS = {
    "douyin": {
        "base": {
            "speed": 1.3,        # 语速快
            "pitch": 2,          # 略高音
            "energy": 1.3,       # 能量高
            "pause_between": 0.2  # 分条消息间隔短
        },
        "emotion_modifiers": {
            "excited": {"speed": 1.5, "pitch": 3, "energy": 1.5},
            "happy": {"speed": 1.3, "pitch": 2, "energy": 1.3},
            "neutral": {"speed": 1.2, "pitch": 1, "energy": 1.1},
            "annoyed": {"speed": 1.4, "pitch": 0, "energy": 1.2},
            "angry": {"speed": 1.5, "pitch": -1, "energy": 1.4},
            "broken": {"speed": 0.9, "pitch": -2, "energy": 0.8}
        }
    },
    "zhihu": {
        "base": {
            "speed": 0.9,        # 语速慢，显得深思熟虑
            "pitch": -1,         # 略低沉
            "energy": 0.9,       # 能量适中
            "pause_between": 0.5  # 分段间停顿长
        },
        "emotion_modifiers": {
            "excited": {"speed": 1.0, "pitch": 0, "energy": 1.1},
            "happy": {"speed": 0.95, "pitch": 0, "energy": 1.0},
            "neutral": {"speed": 0.9, "pitch": -1, "energy": 0.9},
            "annoyed": {"speed": 1.0, "pitch": -2, "energy": 1.0},
            "angry": {"speed": 1.1, "pitch": -2, "energy": 1.2},
            "broken": {"speed": 0.8, "pitch": -3, "energy": 0.7}
        }
    },
    "xiaohongshu": {
        "base": {
            "speed": 1.1,        # 语速偏快
            "pitch": 3,          # 高音，甜美
            "energy": 1.2,       # 能量较高
            "pause_between": 0.3
        },
        "emotion_modifiers": {
            "excited": {"speed": 1.3, "pitch": 4, "energy": 1.4},
            "happy": {"speed": 1.2, "pitch": 3, "energy": 1.3},
            "neutral": {"speed": 1.1, "pitch": 2, "energy": 1.1},
            "annoyed": {"speed": 1.0, "pitch": 1, "energy": 1.0},
            "angry": {"speed": 1.2, "pitch": 0, "energy": 1.2},
            "broken": {"speed": 0.9, "pitch": 1, "energy": 0.8}
        }
    },
    "weibo": {
        "base": {
            "speed": 1.2,        # 语速快
            "pitch": 1,          # 正常偏高
            "energy": 1.2,       # 能量高
            "pause_between": 0.25
        },
        "emotion_modifiers": {
            "excited": {"speed": 1.4, "pitch": 3, "energy": 1.5},
            "happy": {"speed": 1.2, "pitch": 2, "energy": 1.3},
            "neutral": {"speed": 1.1, "pitch": 1, "energy": 1.1},
            "annoyed": {"speed": 1.2, "pitch": 0, "energy": 1.1},
            "angry": {"speed": 1.3, "pitch": -1, "energy": 1.3},
            "broken": {"speed": 0.9, "pitch": -1, "energy": 0.8}
        }
    },
    "x_twitter": {
        "base": {
            "speed": 1.0,        # 正常语速
            "pitch": 0,          # 中性
            "energy": 1.0,       # 适中
            "pause_between": 0.4
        },
        "emotion_modifiers": {
            "excited": {"speed": 1.1, "pitch": 1, "energy": 1.2},
            "happy": {"speed": 1.0, "pitch": 0, "energy": 1.1},
            "neutral": {"speed": 1.0, "pitch": 0, "energy": 1.0},
            "annoyed": {"speed": 1.1, "pitch": -1, "energy": 1.1},
            "angry": {"speed": 1.2, "pitch": -2, "energy": 1.2},
            "broken": {"speed": 0.85, "pitch": -2, "energy": 0.75}
        }
    },
    "tieba": {
        "base": {
            "speed": 1.0,        # 正常
            "pitch": -2,         # 低沉
            "energy": 0.9,       # 略低，慵懒
            "pause_between": 0.4
        },
        "emotion_modifiers": {
            "excited": {"speed": 1.1, "pitch": -1, "energy": 1.1},
            "happy": {"speed": 1.0, "pitch": -1, "energy": 1.0},
            "neutral": {"speed": 1.0, "pitch": -2, "energy": 0.9},
            "annoyed": {"speed": 1.1, "pitch": -3, "energy": 1.0},
            "angry": {"speed": 1.2, "pitch": -3, "energy": 1.2},
            "broken": {"speed": 0.85, "pitch": -4, "energy": 0.7}
        }
    }
}


class FishAudioTTS:
    """Fish Audio TTS 客户端"""
    
    API_BASE = "https://api.fish.audio"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        default_voice_id: Optional[str] = None,
        cache_dir: str = "./audio_cache"
    ):
        self.api_key = api_key or os.getenv("FISH_AUDIO_API_KEY", "")
        self.default_voice_id = default_voice_id or os.getenv("FISH_AUDIO_REF_ID", "")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载平台配置
        self.platform_configs = PLATFORM_VOICE_CONFIGS
        
        # 每个平台的音色ID配置（从环境变量加载）
        self.platform_voice_ids = {
            "douyin": os.getenv("FISH_VOICE_DOUYIN", ""),
            "zhihu": os.getenv("FISH_VOICE_ZHIHU", ""),
            "xiaohongshu": os.getenv("FISH_VOICE_XIAOHONGSHU", ""),
            "weibo": os.getenv("FISH_VOICE_WEIBO", ""),
            "x": os.getenv("FISH_VOICE_X", ""),
            "tieba": os.getenv("FISH_VOICE_TIEBA", ""),
        }
    
    def get_voice_id_for_platform(self, platform_id: str) -> str:
        """获取平台对应的音色ID"""
        # 优先使用平台专属音色，否则使用默认音色
        return self.platform_voice_ids.get(platform_id, "") or self.default_voice_id
    
    def is_enabled(self) -> bool:
        """检查TTS是否可用"""
        return bool(self.api_key)
    
    def _get_cache_path(self, text: str, config: VoiceConfig) -> Path:
        """获取缓存路径"""
        # 基于文本和配置生成唯一hash
        config_str = f"{config.speed}_{config.pitch}_{config.energy}_{config.emotion}"
        hash_input = f"{text}_{config_str}"
        file_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        return self.cache_dir / f"{file_hash}.mp3"
    
    def get_voice_config(
        self,
        platform_id: str,
        emotion_level: str = "neutral"
    ) -> VoiceConfig:
        """获取平台语音配置"""
        if platform_id not in self.platform_configs:
            platform_id = "douyin"  # 默认
        
        config = self.platform_configs[platform_id]
        base = config["base"]
        modifiers = config["emotion_modifiers"].get(emotion_level, {})
        
        # 使用平台专属音色ID
        voice_id = self.get_voice_id_for_platform(platform_id)
        
        return VoiceConfig(
            reference_id=voice_id,
            speed=modifiers.get("speed", base["speed"]),
            pitch=modifiers.get("pitch", base["pitch"]),
            energy=modifiers.get("energy", base["energy"]),
            emotion=emotion_level,
            pause_between=base["pause_between"]
        )
    
    async def synthesize(
        self,
        text: str,
        config: VoiceConfig,
        use_cache: bool = True
    ) -> bytes:
        """合成语音"""
        # 检查缓存
        cache_path = self._get_cache_path(text, config)
        if use_cache and cache_path.exists():
            return cache_path.read_bytes()
        
        # 调用 Fish Audio API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "reference_id": config.reference_id,
            "format": "mp3",
            "mp3_bitrate": 128,
            "normalize": True,
            "latency": "normal",
            # 语音调整参数
            "prosody": {
                "speed": config.speed,
                "pitch": config.pitch,
                "volume": config.energy
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.API_BASE}/v1/tts",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"TTS API error: {response.status} - {error_text}")
                
                audio_data = await response.read()
        
        # 保存缓存
        if use_cache:
            cache_path.write_bytes(audio_data)
        
        return audio_data
    
    async def synthesize_multi_part(
        self,
        parts: List[str],
        platform_id: str,
        emotion_level: str = "neutral"
    ) -> List[Dict[str, Any]]:
        """
        合成分条消息（抖音风格）
        返回每条消息的音频数据和时间信息
        """
        config = self.get_voice_config(platform_id, emotion_level)
        results = []
        
        for i, part in enumerate(parts):
            if not part.strip():
                continue
            
            audio_data = await self.synthesize(part, config)
            
            results.append({
                "index": i,
                "text": part,
                "audio": audio_data,
                "pause_after": config.pause_between if i < len(parts) - 1 else 0
            })
        
        return results
    
    async def synthesize_with_emotion_shift(
        self,
        text: str,
        platform_id: str,
        start_emotion: str,
        end_emotion: str
    ) -> bytes:
        """
        合成带情绪变化的语音（破防时使用）
        从一种情绪过渡到另一种
        """
        # 简化处理：使用结束情绪
        # 更复杂的实现可以分段处理
        config = self.get_voice_config(platform_id, end_emotion)
        return await self.synthesize(text, config)


class VoiceManager:
    """语音管理器 - 处理整个对话的语音"""
    
    def __init__(self, tts_client: FishAudioTTS):
        self.tts = tts_client
        self.audio_queue: List[Dict] = []
    
    async def process_message(
        self,
        platform_id: str,
        content: str,
        emotion_level: str = "neutral",
        is_multi_part: bool = False,
        parts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """处理一条消息的语音合成"""
        
        if is_multi_part and parts:
            # 分条消息
            audio_parts = await self.tts.synthesize_multi_part(
                parts, platform_id, emotion_level
            )
            return {
                "type": "multi_part",
                "platform": platform_id,
                "parts": audio_parts,
                "total_parts": len(audio_parts)
            }
        else:
            # 单条消息
            config = self.tts.get_voice_config(platform_id, emotion_level)
            audio_data = await self.tts.synthesize(content, config)
            return {
                "type": "single",
                "platform": platform_id,
                "audio": audio_data,
                "text": content
            }
    
    async def process_breakpoint(
        self,
        platform_id: str,
        content: str
    ) -> Dict[str, Any]:
        """处理破防时的语音（带哭腔/颤抖）"""
        config = self.tts.get_voice_config(platform_id, "broken")
        audio_data = await self.tts.synthesize(content, config)
        return {
            "type": "breakpoint",
            "platform": platform_id,
            "audio": audio_data,
            "text": content,
            "emotion": "broken"
        }
    
    async def process_private_message(
        self,
        platform_id: str,
        content: str
    ) -> Dict[str, Any]:
        """处理私信语音（悄悄话感觉，音量略低）"""
        config = self.tts.get_voice_config(platform_id, "neutral")
        # 降低音量模拟悄悄话
        config.energy *= 0.7
        config.speed *= 0.95
        
        audio_data = await self.tts.synthesize(content, config)
        return {
            "type": "private",
            "platform": platform_id,
            "audio": audio_data,
            "text": content
        }
    
    def get_audio_as_base64(self, audio_data: bytes) -> str:
        """将音频数据转为base64（用于前端播放）"""
        return base64.b64encode(audio_data).decode('utf-8')


class MockFishAudioTTS(FishAudioTTS):
    """
    模拟 TTS 客户端（用于测试，不实际调用API）
    """
    
    def __init__(self, *args, **kwargs):
        self.reference_id = kwargs.get('reference_id', 'mock_ref')
        self.platform_configs = PLATFORM_VOICE_CONFIGS
        self.cache_dir = Path('./audio_cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def synthesize(
        self,
        text: str,
        config: VoiceConfig,
        use_cache: bool = True
    ) -> bytes:
        """模拟返回空音频"""
        # 返回一个最小的有效MP3文件头
        return b'\xff\xfb\x90\x00' + b'\x00' * 100


def create_tts_client(
    api_key: Optional[str] = None,
    reference_id: Optional[str] = None,
    use_mock: bool = False
) -> FishAudioTTS:
    """
    创建 TTS 客户端
    
    Args:
        api_key: Fish Audio API key（从环境变量FISH_AUDIO_API_KEY获取）
        reference_id: 参考音频ID（你的唱歌声音，从环境变量FISH_AUDIO_REF_ID获取）
        use_mock: 是否使用模拟客户端
    """
    if use_mock:
        return MockFishAudioTTS()
    
    api_key = api_key or os.getenv("FISH_AUDIO_API_KEY")
    reference_id = reference_id or os.getenv("FISH_AUDIO_REF_ID")
    
    if not api_key:
        raise ValueError("需要提供 FISH_AUDIO_API_KEY")
    if not reference_id:
        raise ValueError("需要提供 FISH_AUDIO_REF_ID（你的唱歌声音ID）")
    
    return FishAudioTTS(api_key, reference_id)


# 使用示例
async def demo():
    """演示用法"""
    # 使用模拟客户端测试
    tts = create_tts_client(use_mock=True)
    manager = VoiceManager(tts)
    
    # 1. 普通消息
    result = await manager.process_message(
        platform_id="zhihu",
        content="谢邀，这个问题我必须认真回答一下。",
        emotion_level="neutral"
    )
    print(f"知乎单条消息: {result['type']}")
    
    # 2. 分条消息（抖音风格）
    result = await manager.process_message(
        platform_id="douyin",
        content="你好装啊@知乎\n我勒个豆\n写论文呢哥们",
        emotion_level="annoyed",
        is_multi_part=True,
        parts=["你好装啊@知乎", "我勒个豆", "写论文呢哥们"]
    )
    print(f"抖音分条消息: {result['total_parts']} 条")
    
    # 3. 破防消息
    result = await manager.process_breakpoint(
        platform_id="xiaohongshu",
        content="我...我只是想分享美好生活...为什么要这样说我..."
    )
    print(f"小红书破防: emotion={result['emotion']}")
    
    # 4. 私信
    result = await manager.process_private_message(
        platform_id="zhihu",
        content="你看抖音那发言，典型的信息茧房受害者"
    )
    print(f"知乎私信: {result['type']}")


if __name__ == "__main__":
    asyncio.run(demo())
