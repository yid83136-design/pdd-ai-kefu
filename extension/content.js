/**
 * 拼多多 AI 客服 - Content Script v3.7
 * =====================================
 * v3.7: 修复轮询吞消息——
 *   scrollHeight 指纹每次新消息都变化，导致 markAllAsSeen() 误吞新消息。
 *   改为用 DOM 元素引用检测对话切换（React 重建容器时引用一定不同）。
 *
 * v3.6: 动态聊天区边界 + 边距比较，不依赖容器中线。
 * v3.5: tick() 加 100ms 等 React 布局；isBuyerMsg 容差 15% + 诊断日志。
 * v3.4: tick() 不再调用 markAllAsSeen()。
 */
(function () {
  "use strict";

  var SERVER = "http://34.81.122.137:5000";
  var autoReply = true;
  var busy = false;
  var seen = new Set();
  var badge = null;
  var instanceId = null;
  var chatBounds = null;  // {left, right} 动态计算的聊天区真实边界

  // ========== 小工具 ==========
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  // ========== 状态指示器 ==========
  function createBadge() {
    if (document.getElementById("__ai_badge__")) return;
    badge = document.createElement("div");
    badge.id = "__ai_badge__";
    Object.assign(badge.style, {
      position: "fixed", zIndex: "999999", top: "10px", right: "20px",
      padding: "6px 14px", borderRadius: "20px", fontSize: "13px",
      color: "#fff", cursor: "pointer", userSelect: "none",
      background: "rgba(0,0,0,0.7)", boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
    });
    badge.addEventListener("click", function () {
      autoReply = !autoReply;
      updateBadge();
    });
    document.body.appendChild(badge);
    updateBadge();
  }

  function updateBadge(state) {
    if (!badge) return;
    if (state === "thinking") badge.innerHTML = "🔵 思考中...";
    else if (state === "error") badge.innerHTML = "🔴 连接失败";
    else if (!autoReply) badge.innerHTML = "🟡 已暂停";
    else badge.innerHTML = "🟢 监听中";
  }

  // ========== 找消息列表容器 ==========
  function findMsgContainer() {
    var best = null, bestArea = 0;
    var all = document.querySelectorAll("*");
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      if (el.scrollHeight <= el.clientHeight + 50) continue;
      if (el.clientHeight <= 200) continue;
      var rect = el.getBoundingClientRect();
      if (rect.top >= window.innerHeight * 0.6) continue;
      var area = rect.width * rect.height;
      if (area > bestArea) { bestArea = area; best = el; }
    }
    return best;
  }

  // ========== 找消息气泡容器（从叶子节点往上爬）==========
  function findBubble(el, container) {
    var node = el;
    var depth = 0;
    while (node && node !== container && node !== document.body && depth < 8) {
      var r = node.getBoundingClientRect();
      if (container) {
        var cw = container.getBoundingClientRect().width;
        if (r.width > cw * 0.25 && r.width < cw * 0.95) return node;
      } else {
        if (r.width > 100 && r.width < window.innerWidth * 0.8) return node;
      }
      node = node.parentElement;
      depth++;
    }
    return el;
  }

  // ========== 判断是否买家发的消息（v3.6 动态边距比较）==========
  // 比较气泡离聊天区左右边界的距离：离左边近→买家触发，离右边近→卖家跳过
  // chatLeft/chatRight 由 scanNewMessages 动态计算后传入
  function isBuyerMsg(el, chatLeft, chatRight) {
    var text = (el.textContent || "").trim();
    if (text.length < 2 || text.length > 2000) return false;

    // 屏蔽系统废话
    var trash = [
      "机器人客服", "转接", "尽快回复", "撤回",
      "保障消费者", "商品全部真实", "该买家", "买家已",
    ];
    for (var i = 0; i < trash.length; i++) {
      if (text.indexOf(trash[i]) !== -1) return false;
    }

    var container = findMsgContainer();
    var bubble = findBubble(el, container);
    var rect = bubble.getBoundingClientRect();

    // 有动态边界 → 用边距比较法（最准）
    if (chatLeft !== undefined && chatRight !== undefined) {
      var distToLeft = rect.left - chatLeft;
      var distToRight = chatRight - rect.right;
      var result = distToLeft < distToRight;
      console.log("[AI判断]", text.slice(0,20).replace(/\n/g," "),
                  "| 距左=" + distToLeft.toFixed(0) + " 距右=" + distToRight.toFixed(0),
                  "| →" + (result ? "买家✅" : "卖家❌"));
      return result;
    }

    // 兜底：没有动态边界时用容器中线
    if (container) {
      var cr = container.getBoundingClientRect();
      var midX = cr.left + cr.width * 0.5;
      var tolerance = cr.width * 0.15;
      return rect.right < midX + tolerance;
    }

    // 最后兜底：屏幕中线
    return rect.left + rect.width * 0.5 < window.innerWidth * 0.5;
  }

  // ========== 调试工具：dump 容器内所有消息位置 ==========
  window.debugDump = function () {
    var container = findMsgContainer();
    if (!container) { console.log("[debugDump] 没找到消息容器"); return; }
    var cr = container.getBoundingClientRect();
    console.log("=== 消息容器: " + container.tagName + "." + (container.className || "").slice(0, 30) + " ===");
    console.log("容器 left=" + cr.left.toFixed(0) + " right=" + cr.right.toFixed(0) + " width=" + cr.width.toFixed(0));

    var items = [];
    var walker = document.createTreeWalker(container, NodeFilter.SHOW_ELEMENT);
    while (walker.nextNode()) {
      var el = walker.currentNode;
      if (el.children.length > 0) continue;
      var text = (el.textContent || "").trim();
      if (text.length < 2 || text.length > 2000) continue;
      var bubble = findBubble(el, container);
      var br = bubble.getBoundingClientRect();
      var leftGap = br.left - cr.left;
      var rightGap = cr.right - br.right;
      var side = isBuyerMsg(el, undefined, undefined) ? "买家" : "卖家";
      items.push({
        text: text.slice(0, 30),
        bub_left: br.left.toFixed(0),
        bub_right: br.right.toFixed(0),
        leftGap: leftGap.toFixed(0),
        rightGap: rightGap.toFixed(0),
        side: side,
      });
    }
    console.table(items);
    console.log("共 " + items.length + " 条消息");
  };
  console.log("[AI] 调试工具已就绪，控制台输入 debugDump() 查看消息位置分布");

  // ========== 把当前所有消息标记为已处理 ==========
  function markAllAsSeen() {
    var container = findMsgContainer();
    if (!container) return;
    var walker = document.createTreeWalker(container, NodeFilter.SHOW_ELEMENT);
    while (walker.nextNode()) {
      var el = walker.currentNode;
      if (el.children.length > 0) continue;
      var text = (el.textContent || "").trim();
      if (text.length >= 2 && text.length <= 2000) {
        seen.add(text.slice(0, 80));
      }
    }
  }

  // ========== 扫描新消息（v3.6 动态聊天区边界）==========
  function scanNewMessages() {
    if (busy) return [];
    var container = findMsgContainer();
    if (!container) return [];

    // 动态计算聊天区真实边界（避开侧边栏干扰）
    // 遍历容器内所有叶子节点，找气泡的最左和最右边缘
    var chatLeft, chatRight;
    var walker2 = document.createTreeWalker(container, NodeFilter.SHOW_ELEMENT);
    var minL = Infinity, maxR = -Infinity;
    while (walker2.nextNode()) {
      var node = walker2.currentNode;
      if (node.children.length > 0) continue;
      if ((node.textContent || "").trim().length < 2) continue;
      var b = findBubble(node, container);
      var br = b.getBoundingClientRect();
      if (br.width > 50 && br.height > 15) {
        if (br.left < minL) minL = br.left;
        if (br.right > maxR) maxR = br.right;
      }
    }
    if (minL < Infinity && maxR > -Infinity) {
      chatLeft = minL;
      chatRight = maxR;
    }

    var results = [];
    var walker = document.createTreeWalker(container, NodeFilter.SHOW_ELEMENT);
    while (walker.nextNode()) {
      var el = walker.currentNode;
      if (el.children.length > 0) continue;
      var text = (el.textContent || "").trim();
      if (text.length < 2 || text.length > 2000) continue;
      var key = text.slice(0, 80);
      if (seen.has(key)) continue;
      seen.add(key);
      if (isBuyerMsg(el, chatLeft, chatRight)) results.push({ el: el, text: text });
    }

    if (seen.size > 500) seen.clear();
    return results;
  }

  // ========== 找输入框 ==========
  function findInput() {
    var inputs = document.querySelectorAll('[contenteditable="true"], textarea, [role="textbox"]');
    for (var i = 0; i < inputs.length; i++) {
      var r = inputs[i].getBoundingClientRect();
      if (r.width > 50 && r.height > 20 && r.top > window.innerHeight * 0.4) return inputs[i];
    }
    return null;
  }

  // ========== 找发送按钮 ==========
  function findSendBtn() {
    var btns = document.querySelectorAll("button, [role='button'], span, div");
    for (var i = 0; i < btns.length; i++) {
      var t = (btns[i].textContent || "").trim();
      if (t === "发送" || t === "发送(S)" || t === "发送(Enter)") {
        var r = btns[i].getBoundingClientRect();
        if (r.width > 20 && r.top > window.innerHeight * 0.4) return btns[i];
      }
    }
    return null;
  }

  // ========== 打字 + 发送 ==========
  async function typeAndSend(text) {
    var input = findInput();
    if (!input) { console.log("[AI] 找不到输入框"); return false; }

    // 清空
    input.focus();
    if (input.tagName === "TEXTAREA" || input.tagName === "INPUT") {
      var proto = Object.getPrototypeOf(input);
      var desc = Object.getOwnPropertyDescriptor(proto, "value");
      if (desc && desc.set) { desc.set.call(input, ""); }
      else { input.value = ""; }
    } else {
      input.textContent = "";
      input.innerHTML = "";
    }
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await sleep(150);

    // 逐字填入
    for (var i = 0; i < text.length; i += 3) {
      var chunk = text.slice(i, i + 3);
      if (input.tagName === "TEXTAREA" || input.tagName === "INPUT") {
        input.value += chunk;
      } else {
        document.execCommand("insertText", false, chunk);
      }
      input.dispatchEvent(new Event("input", { bubbles: true }));
      await sleep(40 + Math.random() * 50);
    }
    await sleep(500);

    var btn = findSendBtn();

    // 方法1: MouseEvent 序列
    if (btn) {
      btn.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0 }));
      btn.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true, button: 0 }));
      btn.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 }));
    }

    // 方法2: React Fiber 穿透
    if (btn) {
      var keys = Object.keys(btn);
      var fiberKey = null;
      for (var j = 0; j < keys.length; j++) {
        if (keys[j].startsWith("__reactFiber") || keys[j].startsWith("__reactInternalInstance")) {
          fiberKey = keys[j];
          break;
        }
      }
      if (fiberKey) {
        var fiber = btn[fiberKey];
        var node = fiber;
        while (node) {
          if (node.memoizedProps) {
            if (node.memoizedProps.onClick) { node.memoizedProps.onClick({}); break; }
            if (node.memoizedProps.onMouseDown) { node.memoizedProps.onMouseDown({}); break; }
          }
          node = node.return;
        }
      }
    }

    // 方法3: Enter 键
    input.dispatchEvent(new KeyboardEvent("keydown", {
      key: "Enter", code: "Enter", keyCode: 13, which: 13,
      bubbles: true, cancelable: true, composed: true,
    }));

    console.log("[AI] 已发送:", text.slice(0, 40) + "...");
    return true;
  }

  // ========== 调用服务器 AI ==========
  async function callAI(msg) {
    try {
      var m = location.href.match(/uid=([^&]+)/);
      var uid = m ? m[1] : "user1";
      var resp = await fetch(SERVER + "/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, user_id: uid, instance_id: instanceId }),
      });
      var data = await resp.json();
      return (data.reply || "").trim();
    } catch (e) {
      console.log("[AI] 请求服务器失败:", e);
      updateBadge("error");
      return "";
    }
  }

  // ========== 主处理循环 ==========
  async function tick() {
    if (!autoReply || busy) return;
    await sleep(100);  // 等 React 完成布局，否则新消息的 getBoundingClientRect() 可能返回中间态
    var msgs = scanNewMessages();
    if (msgs.length === 0) return;

    busy = true;
    updateBadge("thinking");

    var reply = await callAI(msgs[0].text);
    if (reply) {
      // 把 AI 回复文本提前加入 seen，防止自己的回复被当成新消息
      // 在 typeAndSend 之前加——DOM 更新可能在 typeAndSend 完成前就触发 MutationObserver
      seen.add(reply.slice(0, 80));
      await sleep(1000 + Math.random() * 1500);
      await typeAndSend(reply);
      // 不再调用 markAllAsSeen()——它会把客户在 AI 思考期间发的新消息也吞进 seen
    }

    busy = false;
    updateBadge();
  }

  // ========== 启动监听（v3.3 Observer 挂 body）==========
  function startWatch() {
    // Observer 挂在 body 上，不挂在容器上（容器会随切换对话被销毁）
    var timer = null;
    new MutationObserver(function () {
      if (timer) clearTimeout(timer);
      timer = setTimeout(tick, 600);
    }).observe(document.body, { childList: true, subtree: true, characterData: true });

    // 兜底轮询：检测对话切换 + 触发 tick
    var lastContainerEl = null;
    setInterval(function () {
      var container = findMsgContainer();
      // 容器 DOM 元素变了 = React 重建了容器 = 切换了对话
      if (container && container !== lastContainerEl && lastContainerEl !== null) {
        console.log("[AI] 检测到对话切换（容器引用变了），清空去重记忆");
        seen.clear();
        // 不调用 markAllAsSeen()——新对话的现有消息下次轮询自然会被扫到
      }
      lastContainerEl = container;
      tick();
    }, 2500);

    console.log("[AI] 监听已启动（Observer 挂 body，容器动态查找）");
  }

  // ========== 初始化 ==========
  async function init() {
    try {
      var stored = await new Promise(function (resolve) {
        chrome.storage.local.get(["autoReply", "apiKey", "serverUrl"], resolve);
      });
      if (stored.autoReply !== undefined) autoReply = stored.autoReply;
      if (stored.serverUrl) SERVER = stored.serverUrl;

      // 生成或读取本机唯一 ID（用于服务器区分不同卖家）
      var idResult = await new Promise(function (resolve) {
        chrome.storage.local.get(["instanceId"], resolve);
      });
      if (idResult.instanceId) {
        instanceId = idResult.instanceId;
      } else {
        instanceId = "user_" + Math.random().toString(36).substr(2, 9);
        chrome.storage.local.set({ instanceId: instanceId });
      }
      console.log("[AI] 本机ID:", instanceId);

      if (stored.apiKey && stored.apiKey.startsWith("sk-")) {
        fetch(SERVER + "/api/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: stored.apiKey, instance_id: instanceId }),
        }).catch(function () {});
      }
    } catch (e) {}

    createBadge();
    startWatch();

    setTimeout(function () {
      markAllAsSeen();
      console.log("[AI] 已忽略现有消息，等待新买家消息...");
    }, 1500);
    console.log("[AI] 拼多多客服助手 v3.7 启动完成");
  }

  // ========== Popup 通信 ==========
  chrome.runtime.onMessage.addListener(function (msg, sender, respond) {
    if (msg.action === "getStatus") {
      respond({ autoReply: autoReply, busy: busy });
    } else if (msg.action === "setAutoReply") {
      autoReply = msg.value;
      updateBadge();
      respond({ ok: true });
    } else if (msg.action === "ping") {
      respond({ alive: true });
    }
  });

  // ========== 启动 ==========
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
