# 拼多多 AI 客服助手

**自动监听拼多多商家客服消息 → 调用 DeepSeek AI 生成回复 → 自动发送。** 24小时在线，买家消息秒回。

---

## 系统架构

```
买家在拼多多发消息
       ↓
你的 Chrome 浏览器（打开拼多多客服页面）
       ↓ content.js 检测新买家消息
       ↓ POST 到你的服务器
你的 Linux 服务器（Flask + DeepSeek API）
       ↓ AI 生成回复
       ↓ 返回回复文本
 content.js 自动填入输入框 → 点击发送
       ↓
买家收到回复
```

---

## 前置准备

| 你需要有的 | 说明 |
|-----------|------|
| **DeepSeek API Key** | 到 [platform.deepseek.com](https://platform.deepseek.com) 注册，充值 10 元即可。API Key 以 `sk-` 开头 |
| **一台 Linux 服务器** | 任何有公网 IP 的云服务器都行（阿里云/腾讯云/华为云等），1核1G 足够 |
| **Chrome 浏览器** | 版本 88+ |
| **拼多多商家账号** | 能登录 mms.pinduoduo.com 客服后台 |

---

## 第一步：部署服务器

### 1. 上传文件到服务器

在你本地电脑打开 PowerShell 或终端，运行：

```bash
scp "E:\ai客服\server.py" root@你的服务器IP:/root/
scp "E:\ai客服\setup_server.sh" root@你的服务器IP:/root/
```

### 2. SSH 登录服务器

```bash
ssh root@你的服务器IP
```

### 3. 运行一键部署脚本

```bash
chmod +x setup_server.sh
sudo bash setup_server.sh
```

脚本会自动完成：
- 安装 Python3、pip3 和依赖包
- 引导你输入 DeepSeek API Key
- 创建 systemd 服务（崩溃自动重启、开机自启）
- 开放防火墙 5000 端口

### 4. 开放云服务器安全组

**重要！** 如果你用的是阿里云/腾讯云/华为云，还需要在云控制台操作：

> 进入控制台 → 安全组 → 添加入方向规则 → 协议 TCP，端口 5000，来源 0.0.0.0/0 → 保存

### 5. 验证部署是否成功

浏览器打开：`http://你的服务器IP:5000/api/health`

应该看到类似 `{"status":"ok","time":"...","has_api_key":true}` 的 JSON 响应。

---

## 第二步：安装 Chrome 插件

### 1. 加载插件

1. 打开 Chrome 浏览器
2. 地址栏输入 `chrome://extensions`，回车
3. 右上角打开 **「开发者模式」** 开关
4. 点击 **「加载已解压的扩展程序」**
5. 选择文件夹：`E:\ai客服\extension`
6. 完成！工具栏会出现插件图标

### 2. 配置插件

1. 点击浏览器右上角插件图标（找不到的话点拼图图标 → 找到"拼多多 AI 客服" → 点图钉固定）
2. 在弹出面板中填入：
   - **DeepSeek API Key**：你的 `sk-xxx`
   - **服务器地址**：`http://你的服务器IP:5000`
   - **店铺提示词**：可选，留空则使用默认设置
3. 点击 **「保存配置」**
4. 点击 **「测试连接」**，确认显示"连接成功"

---

## 第三步：开始使用

### 1. 打开拼多多客服页面

用 Chrome 访问拼多多商家后台：`https://mms.pinduoduo.com/chat-merchant/index.html#/`

### 2. 确认插件已启动

页面右上角会出现状态标签：

| 状态 | 含义 |
|------|------|
| 🟢 监听中 | 正常工作，等待买家消息 |
| 🔵 思考中 | 正在调用 AI 生成回复 |
| 🟡 已暂停 | 手动关闭了自动回复 |
| 🔴 连接失败 | 无法连接服务器（检查网络） |

### 3. 测试自动回复

用另一个设备或浏览器窗口，用**买家账号**给你的店铺发一条消息。插件会自动检测、调用 AI、填入回复并发送。

### 4. 切换对话

插件支持多买家同时在线。点击左侧联系人列表切换到不同买家，插件会自动识别并处理。

---

## 自定义 AI 回复风格

server.py 里已经内置了一套完整的客服话术体系（覆盖品质、物流、售后、价格等 25+ 场景）。

如果你想定制，有两种方式：

**方式一：通过插件面板（简单）**

点击插件图标 → 在"店铺提示词"框里写你的额外要求 → 保存。这段内容会追加在默认 prompt 后面。

**方式二：直接改 server.py（深度定制）**

编辑服务器上的 `/opt/pdd-kefu/server.py`，找到 `SHOP_PROMPT` 变量，按需修改。改完后重启：

```bash
sudo systemctl restart pdd-kefu
```

---

## 服务器管理命令

```bash
# 查看实时日志
journalctl -u pdd-kefu -f

# 查看最近 50 行日志
journalctl -u pdd-kefu -n 50

# 重启服务（修改 server.py 后需要）
sudo systemctl restart pdd-kefu

# 停止服务
sudo systemctl stop pdd-kefu

# 查看服务状态
systemctl status pdd-kefu
```

---

## 更新插件

当 content.js 有更新时：

1. 把新的 content.js 放到 `E:\ai客服\extension\` 目录
2. 打开 `chrome://extensions`
3. 找到插件，点右下角**刷新图标**（圆圈箭头）
4. 打开拼多多客服页面，按 F5 刷新

---

## 常见问题

**Q：插件加载后打开拼多多页面没有绿色标签？**

- 确认网址是 `mms.pinduoduo.com` 域名
- 在 `chrome://extensions` 点刷新按钮
- 按 F12 → Console，看有没有 `[AI]` 开头的日志
- 确认 `content.js` 和 `manifest.json` 在同一个 `extension` 文件夹里

**Q：能检测到消息但回复发不出去？**

- 按 F12 打开控制台，看是否有报错
- 在控制台输入 `debugDump()` 查看消息定位数据

**Q：AI 回复跟客户问题不相关？**

- 检查 `http://你的服务器IP:5000/api/health` 确认服务正常
- 查看服务器日志：`journalctl -u pdd-kefu -n 30`
- 如果回复模板过时，更新 server.py 里的 SHOP_PROMPT

**Q：过了好久客户发第二条消息不触发？**

- 刷新插件 + F5 刷新页面
- 如果还是不行，检查是不是用了最新的 content.js（v3.7+）

**Q：DeepSeek API 报错？**

常见原因：
- `401`：API Key 错误或过期 → 重新生成 Key
- `402`：账户余额不足 → 充值
- `429`：调用频率过高 → 稍等再试

---

## 费用估算

| 项目 | 费用 |
|------|------|
| DeepSeek API | 每条消息约 500 tokens，输入 ¥1/百万、输出 ¥2/百万。日均 100 条 ≈ ¥0.1 |
| 云服务器 | 1核1G 最低配即可，约 ¥50-100/月（闲置服务器可复用，零额外成本） |
| **合计月费** | **约 ¥50-100（主要是服务器）** |

---

## 文件说明

```
E:\ai客服\
├── server.py                  # Flask 服务器（核心）
├── setup_server.sh            # 服务器一键部署脚本
├── requirements_server.txt    # Python 依赖列表
├── README.md                  # 本文件
└── extension\
    ├── manifest.json          # Chrome 插件配置
    ├── content.js             # 页面注入脚本（核心）
    ├── popup.html             # 插件弹出设置面板
    ├── popup.js               # 弹出面板逻辑
    └── icon.png               # 插件图标
```

---

## 技术栈

- **前端**：Chrome Extension Manifest V3、原生 JavaScript
- **后端**：Python Flask + Gunicorn
- **AI**：DeepSeek Chat API（兼容 OpenAI 格式）
- **部署**：Linux systemd 服务
