# 飞书 × Claude 机器人

将 Claude AI 接入飞书，支持私聊和群聊（群聊需 @ 机器人触发）。

---

## 一、在飞书开放平台创建应用

1. 打开 [飞书开放平台](https://open.feishu.cn/app) → **创建企业自建应用**
2. 进入应用 → **添加应用能力** → 开启 **机器人**
3. 记录以下信息（后面要用）：
   - `App ID`
   - `App Secret`
4. 在左侧菜单 **事件订阅** 中，记录：
   - `Verification Token`
5. 在 **权限管理** 中开启以下权限：
   - `im:message`（接收消息）
   - `im:message:send_as_bot`（发送消息）

---

## 二、部署到 Render（永久免费）

> Render 免费套餐无需绑定信用卡，适合飞书机器人这类轻量服务。
> ⚠️ 唯一注意：免费实例**15 分钟无请求会进入休眠**，飞书消息到来时会自动唤醒，首次响应约慢 30 秒。

### 2.1 准备代码仓库

将本项目上传到 GitHub（免费注册）：

```bash
git init
git add .
git commit -m "init feishu claude bot"
# 在 GitHub 创建新仓库后：
git remote add origin https://github.com/你的用户名/feishu-claude-bot.git
git push -u origin main
```

### 2.2 在 Render 部署

1. 打开 [render.com](https://render.com) → 用 GitHub 账号注册/登录
2. 点击 **New** → **Web Service**
3. 选择刚才的 GitHub 仓库，点击 **Connect**
4. 填写以下配置：

| 配置项 | 填写内容 |
|--------|---------|
| Name | `feishu-claude-bot`（随意） |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | **Free** |

5. 点击 **Create Web Service**，等待部署完成（约 2 分钟）

### 2.3 配置环境变量

在 Render 项目页面 → **Environment** 标签 → 添加以下变量：

| 变量名 | 说明 |
|--------|------|
| `FEISHU_APP_ID` | 飞书应用的 App ID |
| `FEISHU_APP_SECRET` | 飞书应用的 App Secret |
| `FEISHU_VERIFY_TOKEN` | 飞书事件订阅的 Verification Token |
| `FEISHU_ENCRYPT_KEY` | 飞书加密密钥（未开启则留空） |
| `ANTHROPIC_API_KEY` | Anthropic API Key |

添加完成后点击 **Save Changes**，服务会自动重启。

### 2.4 获取公网地址

Render 部署成功后，页面顶部会显示公网地址，格式类似：

```
https://feishu-claude-bot-xxxx.onrender.com
```

---

## 三、在飞书配置 Webhook

1. 回到飞书开放平台 → 你的应用 → **事件订阅**
2. **请求网址**填写：
   ```
   https://你的render地址/webhook/feishu
   ```
3. 点击**验证**，看到"验证成功"即可
4. 在下方**订阅事件**中添加：`接收消息 (im.message.receive_v1)`
5. 保存并**发布应用**

---

## 四、测试

- **私聊**：在飞书中找到你的机器人，发送任意消息
- **群聊**：将机器人添加到群，发送消息时 @ 机器人

机器人会调用 Claude 并在几秒内回复 ✅

---

## 五、本地开发（可选）

```bash
# 安装依赖
pip install -r requirements.txt

# 复制并填写环境变量
cp .env.example .env

# 启动服务
uvicorn main:app --reload --port 8000

# 使用 ngrok 暴露本地端口（用于飞书回调测试）
ngrok http 8000
```

---

## 常见问题

**Q: 机器人没有回复？**
- 检查 Render 的日志（项目页面 → Logs 标签）
- 确认环境变量都填写正确
- 确认飞书应用权限已发布

**Q: 群聊没有回复？**
- 群聊中必须 @ 机器人才会触发
- 确认机器人已被添加到群

**Q: 签名验证失败？**
- 检查 `FEISHU_VERIFY_TOKEN` 是否与飞书后台一致

**Q: 第一条消息响应很慢（约 30 秒）？**
- 这是 Render 免费套餐的休眠机制：15 分钟无请求后实例会休眠
- 飞书消息到来时会自动唤醒，唤醒后恢复正常速度
- 如需避免休眠，可升级到 Render Starter 套餐（$7/月）
