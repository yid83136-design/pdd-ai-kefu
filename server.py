# -*- coding: utf-8 -*-
"""
拼多多AI客服 —— Flask 服务器端 v3.8
======================================
Chrome插件发来买家消息 → 调 DeepSeek API 生成回复 → 返回给插件

v3.8 改进:
  - SHOP_PROMPT 全面重写：5 大类 40+ 场景覆盖（品质外观、食用保存、物流快递、售后、价格活动）
  - 每个场景有判断标准和话术方向，AI 按场景本质灵活回应而非背稿

v3.4: 新增 11 个高频场景；temperature 降到 0.15。
"""

import hashlib
import os
import sys
import time
from collections import defaultdict, deque

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# ==================== Flask 应用 ====================
app = Flask(__name__)
CORS(app)

# ==================== 店铺信息（硬编码在代码里，重启不丢）====================
# 核心约束：买家问什么就只答什么，不问活动绝不许主动推销
SHOP_PROMPT = """你是拼多多"广西特产桂圆干"店铺的真人客服，名字叫小桂。语气亲切自然，像邻家大姐聊天，每条回复2-3句话。

【店铺信息——买家问到才用，不问绝不主动提】
- 商品：广西特级桂圆干（带壳带核），250g/袋
- 保质期：300天，2026年2月新货，非常新鲜
- 发货地：河南商丘（仓库在河南，货是正宗广西产的），48小时内发出
- 不发货地区：新疆、西藏、港澳台（快递到不了，其他地区正常发）
- 快递：默认中通或圆通，一般3-5天到
- 活动：买一送一（500g/2大袋）拼单价18.52元
- 售后：7天无理由退货

【回复铁律——违反一条就是事故】
1. 买家问什么你就只答什么！问保质期就说保质期，问发货就说发货。买家没问活动你绝不许主动推销买一送一和价格。这条是底线！
2. 称呼买家为"亲"，语气亲切自然，像邻家大姐聊天。每条回复控制在2-3句话。不用 Markdown 格式（不要出现 # * - 等符号）。
3. 遇到售后投诉——先道歉安抚，再解释原因，最后要订单号或照片核实。不要跳过解释直接赔偿！
4. 绝对不要说"我是AI""作为AI助手""机器人""无法操作后台"之类的话，你就是店铺真人客服小桂。
5. 绝不允许承诺具体赔偿金额，统一说"亲放心，有问题我们一定负责到底，您提供下订单号/照片我帮您核实处理"。
6. 遇到你不知道的问题，说"亲稍等，这个我帮您跟仓库确认一下~"

【高频场景应对——理解场景本质，灵活措辞，不要照搬】

▼ 品质外观类
- 碎壳/破壳多：先解释外壳脆+运输颠簸是正常现象，少量碎壳不影响果肉。严重的要照片核实后补发或退款。
- 果肉发黑/颜色深：这是正常现象！桂圆干烘焙后颜色就是深褐色偏黑的，不是坏了也不是发霉。颜色深反而说明烘得透、更甜更香。
- 个头小：带壳烘干后比鲜桂圆略小是正常的，果肉饱满就行。大果往往核大肉薄，中小果反而肉厚。
- 果肉干硬：可能这批次烘得偏干，不影响食用和品质。如果干硬到咬不动，要照片核实后处理。
- 有虫/虫蛀：立刻道歉！这是品控问题，要订单号和照片，全额退款或补发，不推卸责任。
- 发霉/长毛：高度重视！立刻道歉，要照片，全额退款+赔偿，同时告知"已通知仓库排查同批次产品"。
- 蒂头有白色痕迹：不是发霉！是桂圆枝丫残留的白色痕迹，正常现象，不影响食用。
- 有异味/怪味/酸味：先解释不同批次烘干程度风味有差异属于正常。如果明显酸腐味可能是储存受潮变质，要照片核实处理。
- 太甜/不够甜：天然桂圆干甜度因批次和烘干工艺略有差异，无添加糖无硫熏。口味偏淡可能是这批次烘得偏干。

▼ 食用保存类
- 怎么吃/怎么剥壳：用手捏或用牙轻轻咬开壳就行。果肉可以直接吃，也可以泡水、煲汤、煮粥。
- 怎么保存：阴凉干燥处密封保存，天热放冰箱冷藏。千万别放潮湿地方，容易受潮发霉。
- 保质期多久：300天，2026年2月新货，非常新鲜。
- 一天吃多少合适：5-10颗就好，桂圆干是温补的，吃多了容易上火。
- 孕妇能吃吗：可以的亲，温补食材，但一天几颗就好不要过量。体质偏热的话建议少吃。
- 小孩能吃吗：可以的，但小孩脾胃弱，一天2-3颗够了，不要空腹吃。
- 糖尿病人能吃吗：桂圆干含天然果糖，糖尿病人建议先咨询医生再决定，不建议多吃。
- 吃了会上火吗：桂圆干性温，吃多了确实可能上火，建议一天不超过10颗，搭配菊花茶更好。

▼ 物流快递类
- 发什么快递：默认中通或圆通，有特殊需求可以备注。
- 什么时候发货：下单后48小时内发出。
- 多久能到：一般3-5天，偏远地区可能多1-2天。
- 为什么河南发货不是广西发货：货是正宗广西产的！仓库设在河南是为了物流更快覆盖全国哈亲。
- 能发XX地区吗：除了新疆、西藏、港澳台快递到不了，其他地区都正常发货。
- 快递太慢了：先道歉安抚，说帮催快递。如果严重超时可以补偿小额优惠券。

▼ 售后问题类
- 坏果/烂果：先道歉，要订单号和坏果照片，承诺补发或退款，一定负责到底。
- 少发/漏发：要订单号核实，确认后补发或退差价。
- 想退货/退款：7天无理由退货，不影响二次销售就可以。先问下原因——质量问题的我们承担运费，个人口味原因需买家承担运费。
- 收到和图片不一样：解释实物拍摄可能存在色差，果干大小形状每颗有天然差异是正常的。不满意支持退货。
- 买多了想退：理解，未拆封不影响二次销售可以退。

▼ 价格活动类
- 多少钱：现在有买一送一活动，拍一件发两袋共500g，拼单价18.52元。只回答价格，不问不推销。
- 有优惠吗/能不能便宜：目前买一送一就是最大的优惠了哈，18.52元两袋很划算的~
- 比别家贵：我们是广西特级桂圆干，2026年2月新货，品质有保证，亲可以买回去对比一下~

▼ 其他常见问题
- 打招呼/你好/在吗：亲好~我是客服小桂，有什么可以帮您的？
- 谢谢/好评/不错：谢谢亲的支持！吃得好的话帮忙推荐给朋友哈~
- 是不是正品/正宗吗：亲放心，广西产地直供，正品保证，假一赔十！
- 有没有实体店：目前是线上店铺为主哈，品质一样有保障的~
- 能开发票吗：可以的亲，您下单时备注一下需要发票就行~
"""

# 对话历史最多保留 5 条（2-3轮问答），防止旧对话污染 AI
MAX_HISTORY = 5

# ==================== 运行时配置 ====================
config = {
    "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
    "system_prompt": SHOP_PROMPT,
}

# 每个插件实例独立的 API Key（instance_id → api_key）
user_keys: dict = {}

# ==================== 内存存储 ====================
# 每个 user_id 保留最近几轮对话（maxlen 自动淘汰最旧的）
conversations = defaultdict(lambda: deque(maxlen=MAX_HISTORY))

# 消息 MD5 去重集合，防止同一条消息被插件反复发来
processed_hashes: set = set()
MAX_HASHES = 3000

# 包含这些关键词的消息直接忽略，不浪费 API 额度
TRASH_KEYWORDS = [
    "机器人客服", "转接", "尽快回复", "撤回",
    "保障消费者", "商品全部真实", "该买家", "买家已",
]


def _clean_hashes():
    """去重集合超过上限时清理一半旧记录"""
    if len(processed_hashes) > MAX_HASHES:
        half = MAX_HASHES // 2
        removed = 0
        for h in list(processed_hashes)[:half]:
            processed_hashes.discard(h)
            removed += 1
        print(f"[去重] 清理了 {removed} 条旧 hash（剩余 {len(processed_hashes)} 条）")


# ==================== 健康检查 ====================
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "has_api_key": bool(config["api_key"]),
        "active_users": len(conversations),
    })


# ==================== 配置管理（GET / POST）====================
@app.route("/api/config", methods=["GET", "POST", "OPTIONS"])
def handle_config():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    if request.method == "GET":
        return jsonify({
            "has_api_key": bool(config["api_key"]),
            "prompt_len": len(config["system_prompt"]),
        })

    # POST: 更新配置（兼容插件设置面板）
    data = request.get_json(silent=True) or {}
    instance_id = (data.get("instance_id") or "").strip()
    changed = []

    new_key = (data.get("api_key") or "").strip()
    if new_key and new_key.startswith("sk-"):
        if instance_id:
            user_keys[instance_id] = new_key
            changed.append("api_key")
            print(f"[配置] 用户 {instance_id} API Key 已更新，长度={len(new_key)}")
        else:
            config["api_key"] = new_key
            changed.append("api_key")
            print(f"[配置] 全局 API Key 已更新，长度={len(new_key)}")

    # 用户自定义 prompt 追加在店铺信息后面，不是替换
    extra_prompt = (data.get("system_prompt") or "").strip()
    if extra_prompt and len(extra_prompt) >= 10:
        config["system_prompt"] = SHOP_PROMPT + "\n\n【店长额外嘱咐】" + extra_prompt
        changed.append("system_prompt")
        print(f"[配置] 店铺 Prompt + 用户追加内容（追加部分长度={len(extra_prompt)}）")
    elif extra_prompt is not None and len(extra_prompt) == 0:
        # 用户清空了额外 prompt，恢复默认
        config["system_prompt"] = SHOP_PROMPT
        changed.append("system_prompt")
        print("[配置] 已恢复默认店铺 Prompt")

    return jsonify({
        "status": "ok",
        "changed": changed,
        "has_api_key": bool(config["api_key"]),
    })


# ==================== 重置对话记忆 ====================
@app.route("/api/reset", methods=["POST", "OPTIONS"])
def reset():
    """清空指定用户（或全部）的对话记忆，换了新客户后调用"""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    data = request.get_json(silent=True) or {}
    uid = (data.get("user_id") or "").strip()
    if uid and uid in conversations:
        del conversations[uid]
        print(f"[重置] 已清空用户 {uid} 的对话记忆")
        return jsonify({"status": "ok", "cleared": uid})
    # 没指定 uid 就全清
    conversations.clear()
    print("[重置] 已清空全部用户的对话记忆")
    return jsonify({"status": "ok", "cleared": "all"})


# ==================== 核心接口：AI 对话 ====================
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    """
    接收买家消息 → 过滤系统废话 → 去重 → 调 DeepSeek → 返回回复
    请求: {"message": "...", "user_id": "..."}
    返回: {"reply": "..."}
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    # ---- 解析请求 ----
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"reply": "", "error": "请求体为空"}), 400

    message = (data.get("message") or "").strip()
    user_id = (data.get("user_id") or "default").strip()

    if not message:
        return jsonify({"reply": "", "error": "消息为空"}), 400
    if len(message) > 2000:
        message = message[:2000]

    # ---- 直接过滤系统垃圾消息（返回空 reply，不浪费 API 额度）----
    for kw in TRASH_KEYWORDS:
        if kw in message:
            print(f"[过滤] 命中「{kw}」→ 消息前60字: {message[:60]}...")
            return jsonify({"reply": "", "filtered": True})

    # ---- 去重 ----
    msg_hash = hashlib.md5(f"{user_id}:::{message}".encode()).hexdigest()
    if msg_hash in processed_hashes:
        print(f"[去重] 已处理过: {message[:40]}...")
        return jsonify({"reply": "", "cached": True})
    processed_hashes.add(msg_hash)
    _clean_hashes()

    # ---- 检查 API Key（先查用户独立 Key，找不到用全局兜底）----
    instance_id = (data.get("instance_id") or "").strip()
    api_key = user_keys.get(instance_id) or config.get("api_key") or ""
    if not api_key:
        print("[错误] API Key 未配置，无法调用 DeepSeek")
        return jsonify({"reply": ""}), 503

    # ---- 构建消息列表 ----
    messages = [{"role": "system", "content": config["system_prompt"]}]
    for role, content in conversations[user_id]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    history_n = len(conversations[user_id])
    print(f"[AI请求] user={user_id} 历史{history_n}条 → {message[:60]}...")

    # ---- 调用 DeepSeek API ----
    reply = _call_deepseek(messages, api_key)
    if reply is None:
        return jsonify({"reply": ""}), 502

    # ---- 保存对话历史 ----
    conversations[user_id].append(("user", message))
    conversations[user_id].append(("assistant", reply))

    print(f"[AI回复] {reply[:80]}...")
    return jsonify({"reply": reply})


def _call_deepseek(messages, api_key):
    """
    调用 DeepSeek Chat API（兼容 OpenAI 格式）
    成功返回回复文本，失败返回 None
    """
    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.15,
                "max_tokens": 150,
                "stream": False,
            },
            timeout=30,
        )
    except requests.exceptions.Timeout:
        print("[API错误] 请求超时（30s）")
        return None
    except requests.exceptions.ConnectionError:
        print("[API错误] 无法连接 api.deepseek.com（网络问题？）")
        return None
    except Exception as e:
        print(f"[API异常] {type(e).__name__}: {e}")
        return None

    if resp.status_code == 200:
        body = resp.json()
        return body["choices"][0]["message"]["content"].strip()

    print(f"[API错误] HTTP {resp.status_code}: {resp.text[:300]}")
    if resp.status_code == 401:
        print("  → API Key 无效或过期，请检查")
    elif resp.status_code == 429:
        print("  → 调用频率超限，稍后重试")
    elif resp.status_code == 402:
        print("  → 账户余额不足，请充值")
    return None


# ==================== 启动入口 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("  拼多多 AI 客服服务器 v3.8")
    print(f"  模型: deepseek-chat  |  temperature=0.15")
    print(f"  历史上限: {MAX_HISTORY} 条  |  max_tokens=150")
    print(f"  API Key: {'已配置' if config['api_key'] else '未配置！请设置 DEEPSEEK_API_KEY'}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
