# 🎭 平台人格群聊 - Streamlit 版

> 部署到 Streamlit Cloud，获取真实可访问的网页链接！

## 🚀 一键部署到 Streamlit Cloud

### 第一步：上传到 GitHub

1. 登录 [GitHub](https://github.com)
2. 点击右上角 **+** → **New repository**
3. 仓库名填：`platform-chat`
4. 选择 **Public**（Streamlit Cloud 免费版需要公开仓库）
5. 点击 **Create repository**
6. 上传本文件夹中的所有文件

### 第二步：部署到 Streamlit Cloud

1. 访问 [Streamlit Cloud](https://share.streamlit.io)
2. 点击 **Sign in with GitHub** 登录
3. 点击 **New app**
4. 选择你的仓库 `platform-chat`
5. Main file path 填：`app.py`
6. 点击 **Deploy!**

### 第三步：配置 API 密钥（可选）

1. 部署成功后，点击右上角 **⋮** → **Settings**
2. 点击 **Secrets**
3. 添加以下内容：

```toml
# LLM API (二选一)
DEEPSEEK_API_KEY = "sk-你的密钥"
# 或
ZHIPU_API_KEY = "你的密钥"

# Fish Audio (你的语音)
FISH_AUDIO_API_KEY = "你的密钥"
FISH_AUDIO_VOICE_ID = "你的音色ID"
```

4. 点击 **Save**

### 第四步：获取你的网页链接 🎉

部署完成后，你会获得一个类似这样的链接：
```
https://你的用户名-platform-chat-app-xxxxx.streamlit.app
```

这就是你的**真实可访问网页**！可以分享给任何人！

---

## 🎤 语音配置说明

| 角色 | 语音来源 | 说明 |
|-----|---------|------|
| **你的发言** | Fish Audio | 用你自己的音色！ |
| **AI平台** | Edge TTS (免费) | 微软语音，无需配置 |

### Fish Audio 配置步骤：

1. 访问 [Fish Audio](https://fish.audio)
2. 注册登录
3. 上传你的声音样本，或选择一个音色
4. 复制音色ID（在URL中）
5. 填入 Streamlit Secrets

---

## 📁 文件结构

```
platform-chat-streamlit/
├── app.py                 # 主应用
├── requirements.txt       # 依赖
├── config/
│   ├── platforms.json     # 平台配置
│   ├── topics.json        # 话题
│   └── secrets.json       # 破防点
└── .streamlit/
    └── config.toml        # Streamlit 配置
```

---

## ❓ 常见问题

**Q: 不配置 API 能用吗？**
A: 能！会使用模拟回复，但建议配置 DeepSeek 或智谱 API 获得更好体验。

**Q: Fish Audio 不配置会怎样？**
A: 你的发言就没有语音，AI 的回复仍然有语音（免费 Edge TTS）。

**Q: 为什么我的语音没有自动播放？**
A: 浏览器安全策略限制，需要先与页面交互一次。

**Q: 部署失败怎么办？**
A: 检查 requirements.txt 是否正确，确保所有文件都上传了。

---

## 🔗 相关链接

- [Streamlit Cloud](https://share.streamlit.io) - 免费部署平台
- [DeepSeek API](https://platform.deepseek.com) - LLM API
- [智谱 API](https://open.bigmodel.cn) - 免费 LLM API
- [Fish Audio](https://fish.audio) - 语音克隆

---

> 🎭 让 AI 平台吵起来，看看谁会先破防！
