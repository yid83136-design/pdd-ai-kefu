# 拼多多 AI 客服助手

自动监听拼多多商家客服消息，调用 DeepSeek 生成回复并自动发送，无需人工值守。

> 完整部署与使用教程见 [`ai客服/README.md`](ai客服/README.md)

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

## 目录结构

| 路径 | 说明 |
|------|------|
| `server.py` | Flask 后端服务（DeepSeek 回复生成） |
| `extension/` | Chrome 插件（消息监听 + 自动回复） |
| `ai客服/` | 主版本（含完整 README 与部署脚本） |
| `ai客服多api/` | 多 API Key 版本（多用户独立 Key） |
| `pdd_ai_kefu.py` | 独立版自动回复脚本（Selenium） |
| `setup_server.sh` | 服务器一键部署脚本 |
| `requirements_server.txt` | Python 依赖 |

## 快速开始

1. 获取 [DeepSeek API Key](https://platform.deepseek.com)，通过环境变量 `DEEPSEEK_API_KEY` 提供（**切勿硬编码在代码中**）
2. 部署后端：上传 `server.py` + `setup_server.sh` 到服务器，执行 `sudo bash setup_server.sh`
3. 安装 Chrome 插件：`chrome://extensions` → 开发者模式 → 加载 `extension/` 文件夹
4. 插件面板中填写服务器地址与 API Key，测试连接后即可使用

## 安全说明

- API Key 一律通过环境变量 `DEEPSEEK_API_KEY` 读取，仓库内无任何硬编码密钥
- 服务器建议仅对必要来源开放 5000 端口
