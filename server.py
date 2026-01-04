#!/usr/bin/env python3
"""
平台人格群聊系统 - FastAPI 后端服务器
提供RESTful API和WebSocket实时通信
"""

import json
import os
import asyncio
import base64
from pathlib import Path
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 路径配置
BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# ==================== 配置加载 ====================

def load_config(name: str) -> dict:
    """加载配置文件"""
    config_path = CONFIG_DIR / f"{name}.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

PLATFORMS = load_config("platforms")
RELATIONSHIPS = load_config("relationships")
TOPICS = load_config("topics")
SECRETS = load_config("secrets")

# 平台音色ID配置
PLATFORM_VOICE_IDS = {
    "douyin": os.getenv("FISH_VOICE_DOUYIN", ""),
    "zhihu": os.getenv("FISH_VOICE_ZHIHU", ""),
    "xiaohongshu": os.getenv("FISH_VOICE_XIAOHONGSHU", ""),
    "weibo": os.getenv("FISH_VOICE_WEIBO", ""),
    "x": os.getenv("FISH_VOICE_X", ""),
    "tieba": os.getenv("FISH_VOICE_TIEBA", ""),
}

# ==================== 导入核心模块 ====================

import sys
sys.path.insert(0, str(BASE_DIR))

from chatbot import PlatformChatBot, DeepSeekAPI, GLM4API, MockLLM, PLATFORMS as BOT_PLATFORMS

# ==================== 数据模型 ====================

class StartSessionRequest(BaseModel):
    platform1: str
    platform2: str
    topic: str

class SendMessageRequest(BaseModel):
    message: str

class PrivateChoiceRequest(BaseModel):
    choice: int  # 0=配合, 1=中立, 2=公开

# ==================== 会话管理 ====================

class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, PlatformChatBot] = {}
        self.llm = self._create_llm()
    
    def _create_llm(self):
        """创建LLM实例"""
        if os.getenv("DEEPSEEK_API_KEY"):
            logger.info("Using DeepSeek API")
            return DeepSeekAPI()
        elif os.getenv("ZHIPU_API_KEY"):
            logger.info("Using GLM-4 API")
            return GLM4API()
        else:
            logger.info("Using MockLLM (no API key configured)")
            return MockLLM()
    
    def create_session(self, session_id: str) -> PlatformChatBot:
        """创建新会话"""
        bot = PlatformChatBot(self.llm)
        self.sessions[session_id] = bot
        return bot
    
    def get_session(self, session_id: str) -> Optional[PlatformChatBot]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """移除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]

session_manager = SessionManager()

# ==================== TTS 服务 ====================

class TTSService:
    """语音合成服务"""
    
    def __init__(self):
        self.api_key = os.getenv("FISH_AUDIO_API_KEY", "")
        self.enabled = bool(self.api_key)
        
    async def synthesize(self, text: str, platform_id: str) -> Optional[str]:
        """合成语音，返回base64编码的音频"""
        if not self.enabled:
            return None
        
        voice_id = PLATFORM_VOICE_IDS.get(platform_id, "")
        if not voice_id:
            return None
        
        try:
            import httpx
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "text": text,
                "reference_id": voice_id,
                "format": "mp3",
                "mp3_bitrate": 128,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.fish.audio/v1/tts",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    audio_data = response.content
                    return base64.b64encode(audio_data).decode('utf-8')
                else:
                    logger.error(f"TTS error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return None

tts_service = TTSService()

# ==================== FastAPI App ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Platform Chat Server starting...")
    yield
    logger.info("Platform Chat Server shutting down...")

app = FastAPI(
    title="平台人格群聊系统",
    description="六大社交平台拟人化AI群聊",
    version="2.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== API 路由 ====================

@app.get("/", response_class=HTMLResponse)
async def index():
    """返回主页面"""
    html_path = BASE_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="index.html not found")

@app.get("/api/platforms")
async def get_platforms():
    """获取平台列表"""
    result = {}
    for pid, pdata in PLATFORMS.items():
        result[pid] = {
            "id": pid,
            "name": pdata.get("name", pid),
            "age": pdata.get("age", ""),
            "mbti": pdata.get("mbti", ""),
            "traits": pdata.get("core_traits", [])[:3],
            "color": pdata.get("color", "#666666"),
        }
    return result

@app.get("/api/topics")
async def get_topics():
    """获取随机话题"""
    import random
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
    return random.sample(all_topics, min(6, len(all_topics)))

@app.post("/api/session/start")
async def start_session(request: StartSessionRequest):
    """开始新会话"""
    import uuid
    session_id = str(uuid.uuid4())
    
    bot = session_manager.create_session(session_id)
    messages = bot.start_session(request.platform1, request.platform2, request.topic)
    
    return {
        "session_id": session_id,
        "messages": [_format_message(m) for m in messages],
        "emotions": bot.get_emotion_display()
    }

@app.post("/api/session/{session_id}/message")
async def send_message(session_id: str, request: SendMessageRequest):
    """发送消息"""
    bot = session_manager.get_session(session_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Session not found")
    
    new_messages, private_msg, effect = await bot.process_message(request.message)
    
    # 格式化消息
    formatted_messages = [_format_message(m) for m in new_messages]
    
    # 为平台消息生成语音
    for msg in formatted_messages:
        if msg["role"] == "platform" and tts_service.enabled:
            audio = await tts_service.synthesize(msg["content"], msg["platform_id"])
            if audio:
                msg["audio"] = audio
    
    return {
        "messages": formatted_messages,
        "private_message": _format_private_msg(private_msg) if private_msg else None,
        "effect": effect,
        "emotions": bot.get_emotion_display()
    }

@app.post("/api/session/{session_id}/private-choice")
async def handle_private_choice(session_id: str, request: PrivateChoiceRequest):
    """处理私信选择"""
    bot = session_manager.get_session(session_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = bot.process_private_choice(request.choice)
    
    return {
        "result": result,
        "emotions": bot.get_emotion_display()
    }

@app.post("/api/session/{session_id}/end")
async def end_session(session_id: str):
    """结束会话"""
    bot = session_manager.get_session(session_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Session not found")
    
    summary = bot.end_session()
    session_manager.remove_session(session_id)
    
    return summary

@app.get("/api/tts/status")
async def get_tts_status():
    """获取TTS状态"""
    return {
        "enabled": tts_service.enabled,
        "voice_configs": {
            pid: bool(vid) for pid, vid in PLATFORM_VOICE_IDS.items()
        }
    }

# ==================== 辅助函数 ====================

def _format_message(msg) -> dict:
    """格式化消息"""
    return {
        "role": msg.role,
        "content": msg.content,
        "platform_id": msg.platform_id,
        "is_breakpoint": msg.is_breakpoint,
        "is_betrayal": msg.is_betrayal,
        "timestamp": msg.timestamp
    }

def _format_private_msg(msg: dict) -> dict:
    """格式化私信"""
    if not msg:
        return None
    return {
        "from_platform": msg.get("from_platform", ""),
        "content": msg.get("content", ""),
        "type": msg.get("type", "gossip"),
        "target": msg.get("target", "")
    }

# ==================== 主入口 ====================

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
