"""
拼多多 AI 客服自动回复脚本
使用 DeepSeek API 自动回复买家消息

使用方法：
1. 安装依赖：pip install selenium requests webdriver-manager
2. 修改下方配置区域（YOUR_API_KEY 等）
3. 双击运行此脚本，或在终端执行 python pdd_ai_kefu.py
"""

import os
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
#  ★ 配置区域 - 只需修改这里 ★
# ============================================================

# 你的 DeepSeek API Key（在 platform.deepseek.com 获取）
# 建议通过环境变量 DEEPSEEK_API_KEY 提供，避免泄露
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# 你的店铺信息（AI 会根据这些信息回复买家）
SHOP_INFO = """
你是一名专业的拼多多店铺客服，用热情、简洁的语气回复买家，称呼买家为"亲"。

【店铺信息】
- 卖什么：请填写你的商品类型，例如：女装、手机配件、食品等
- 发货时间：付款后48小时内发货，节假日顺延1-2天
- 使用快递：圆通/中通，偏远地区可能需要补运费
- 退换货：支持7天无理由退换，退货运费买家承担
- 发票：不支持开发票

【回复规则】
1. 回复简洁，不超过80字
2. 不能回答的问题说："亲，这个问题稍复杂，我帮您转人工处理～"
3. 不要编造订单信息或物流信息
4. 遇到投诉、纠纷类问题，说转人工
"""

# 检查新消息的间隔时间（秒），建议3-5秒
CHECK_INTERVAL = 3

# ============================================================
#  以下代码无需修改
# ============================================================

# 记录已回复过的消息，防止重复回复
replied_messages = set()

def ask_deepseek(user_message):
    """调用 DeepSeek API 生成回复"""
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": SHOP_INFO},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 200,
                "temperature": 0.7
            },
            timeout=15
        )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[DeepSeek 调用失败] {e}")
        return None


def get_latest_buyer_message(driver):
    """获取当前对话中最新的买家消息"""
    try:
        # 拼多多客服页面的买家消息选择器
        messages = driver.find_elements(
            By.CSS_SELECTOR,
            ".msg-item.msg-left .msg-content, .message-item.left .content, .chat-message.receive .text"
        )
        if messages:
            last_msg = messages[-1]
            msg_text = last_msg.text.strip()
            return msg_text
        return None
    except Exception as e:
        print(f"[获取消息失败] {e}")
        return None


def send_reply(driver, reply_text):
    """在输入框输入回复并发送"""
    try:
        # 尝试多种输入框选择器
        input_selectors = [
            ".input-area textarea",
            ".chat-input textarea",
            "textarea.msg-input",
            "[contenteditable='true']",
            ".editor-container [contenteditable]"
        ]
        
        input_box = None
        for selector in input_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    input_box = elements[0]
                    break
            except:
                continue
        
        if not input_box:
            print("[找不到输入框]")
            return False
        
        input_box.click()
        time.sleep(0.5)
        
        # 清空输入框并输入回复
        input_box.send_keys(Keys.CONTROL + "a")
        input_box.send_keys(reply_text)
        time.sleep(0.5)
        
        # 按回车发送
        input_box.send_keys(Keys.RETURN)
        print(f"[已发送回复] {reply_text[:30]}...")
        return True
        
    except Exception as e:
        print(f"[发送回复失败] {e}")
        return False


def main():
    print("=" * 50)
    print("  拼多多 AI 客服自动回复脚本")
    print("  使用 DeepSeek API")
    print("=" * 50)
    print()
    
    # 检查 API Key 是否已配置
    if "xxxxxxxx" in DEEPSEEK_API_KEY:
        print("❌ 请先在脚本顶部填写你的 DeepSeek API Key！")
        input("按回车键退出...")
        return
    
    print("正在启动 Chrome 浏览器...")
    
    # 启动 Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,800")
    # 使用你已登录的 Chrome 配置（保留登录状态）
       
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
    except Exception as e:
        print(f"❌ 启动 Chrome 失败：{e}")
        print("请确保已安装 Chrome 浏览器")
        input("按回车键退出...")
        return
    
    print("✅ Chrome 启动成功")
    print("正在打开拼多多客服页面...")
    
    driver.get("https://mms.pinduoduo.com/chat-merchant/index.html#/")
    time.sleep(3)
    
    print("✅ 页面已打开")
    print()
    print("⚠️  如果需要登录，请在浏览器中手动登录")
    print("登录完成后脚本会自动开始监听消息")
    print()
    print("按 Ctrl+C 可以停止脚本")
    print("-" * 50)
    
    # 等待页面加载完成
    time.sleep(5)
    
    last_message = None
    
    while True:
        try:
            # 获取最新买家消息
            current_message = get_latest_buyer_message(driver)
            
            if current_message and current_message != last_message:
                # 生成唯一标识防止重复回复
                msg_id = hash(current_message)
                
                if msg_id not in replied_messages:
                    print(f"[新消息] {current_message[:50]}")
                    
                    # 调用 DeepSeek 生成回复
                    reply = ask_deepseek(current_message)
                    
                    if reply:
                        time.sleep(1)  # 模拟思考延迟
                        success = send_reply(driver, reply)
                        
                        if success:
                            replied_messages.add(msg_id)
                            last_message = current_message
                            print(f"[DeepSeek 回复] {reply[:50]}")
                    else:
                        print("[DeepSeek 未返回回复，跳过]")
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n脚本已停止")
            break
        except Exception as e:
            print(f"[运行错误] {e}")
            time.sleep(5)
    
    driver.quit()
    print("浏览器已关闭")


if __name__ == "__main__":
    main()
