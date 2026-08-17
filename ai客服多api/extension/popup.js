/**
 * 拼多多 AI 客服 - 弹窗设置面板脚本
 * ===================================
 * 功能：读写 chrome.storage.local，保存配置并同步到服务器，测试连接
 */
(function () {
  "use strict";

  var apiKeyInput = document.getElementById("apiKey");
  var serverUrlInput = document.getElementById("serverUrl");
  var promptInput = document.getElementById("prompt");
  var saveBtn = document.getElementById("saveBtn");
  var testBtn = document.getElementById("testBtn");
  var statusArea = document.getElementById("statusArea");

  // ---- 显示状态提示 ----
  function showStatus(msg, type) {
    statusArea.textContent = msg;
    statusArea.className = "show " + type;
    // 4 秒后自动消失
    setTimeout(function () { statusArea.className = ""; }, 4000);
  }

  // ---- 加载已保存的配置 ----
  chrome.storage.local.get(["apiKey", "serverUrl", "prompt"], function (data) {
    if (data.apiKey) apiKeyInput.value = data.apiKey;
    if (data.serverUrl) serverUrlInput.value = data.serverUrl;
    if (data.prompt) promptInput.value = data.prompt;
  });

  // ---- 保存配置 ----
  saveBtn.addEventListener("click", function () {
    var apiKey = apiKeyInput.value.trim();
    var serverUrl = serverUrlInput.value.trim() || "http://34.81.122.137:5000";
    var prompt = promptInput.value.trim();

    if (!serverUrl) {
      showStatus("请输入服务器地址", "err");
      return;
    }

    // 生成或读取本机唯一 ID
    chrome.storage.local.get(["instanceId"], function (idResult) {
      var instanceId = idResult.instanceId;
      if (!instanceId) {
        instanceId = "user_" + Math.random().toString(36).substr(2, 9);
        chrome.storage.local.set({ instanceId: instanceId });
      }

      chrome.storage.local.set({
        apiKey: apiKey,
        serverUrl: serverUrl,
        prompt: prompt,
      }, function () {
        if (apiKey && apiKey.startsWith("sk-")) {
          var body = { api_key: apiKey, instance_id: instanceId };
          if (prompt) body.system_prompt = prompt;

          fetch(serverUrl + "/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }).then(function (r) { return r.json(); })
            .then(function (d) {
              if (d && d.status === "ok") {
                showStatus("配置已保存并同步到服务器 ✓\n您的店铺ID: " + instanceId, "ok");
              } else {
                showStatus("配置已保存到本地，但服务器返回异常", "warn");
              }
            }).catch(function () {
              showStatus("配置已保存到本地，但服务器连接失败", "warn");
            });
        } else {
          showStatus("配置已保存（API Key 为空或格式不对，未同步到服务器）", "ok");
        }
      });
    });
  });

  // ---- 测试连接 ----
  testBtn.addEventListener("click", function () {
    var serverUrl = serverUrlInput.value.trim() || "http://34.81.122.137:5000";
    showStatus("正在测试连接...", "info");

    fetch(serverUrl + "/api/health")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d && d.status === "ok") {
          showStatus(
            "连接成功！服务器时间: " + d.time +
            " | API Key: " + (d.has_api_key ? "已配置" : "未配置") +
            " | 活跃用户: " + d.active_users,
            "ok"
          );
        } else {
          showStatus("服务器返回异常: " + JSON.stringify(d), "err");
        }
      })
      .catch(function () {
        showStatus("无法连接服务器，请检查地址和网络是否正常", "err");
      });
  });
})();
