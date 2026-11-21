/**
 * 接口请求封装
 * Author: 王昱皓
 *
 * 统一处理：拼接 /api 前缀、注入 JWT、解析 JSON、错误提示、401 跳登录。
 * 所有页面只调用这里的 get/post/put/del，不直接写 fetch。
 */

const API_BASE = "/api";
const TOKEN_KEY = "sh_token";
const USER_KEY = "sh_user";

/** 读取本地 token */
function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

/** 保存登录态 */
function saveAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user || {}));
}

/** 清除登录态 */
function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** 读取当前用户（未登录返回 null） */
function currentUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

/**
 * 底层请求
 * @param {string} method HTTP 方法
 * @param {string} path 接口路径，如 /goods/1
 * @param {object} [body] 请求体
 */
async function request(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;

  let resp;
  try {
    resp = await fetch(API_BASE + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    toast("网络异常，请确认服务已启动", "error");
    throw err;
  }

  // 登录失效：清空并回登录页
  if (resp.status === 401) {
    if (!location.pathname.endsWith("login.html")) {
      clearAuth();
      location.href = "login.html?redirect=" + encodeURIComponent(location.pathname);
    } else {
      const data = await resp.json();
      toast(data.detail || "用户名或密码错误", "error");
    }
    throw new Error("认证失败");
  }

  const text = await resp.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch (e) {
    throw new Error("服务器响应格式错误");
  }

  if (!resp.ok) {
    // 后端统一异常格式：{ detail: "提示文案" }
    const msg = (data && (data.detail || data.message)) || "请求失败(" + resp.status + ")";
    toast(msg, "error");
    throw new Error(msg);
  }
  return data;
}

const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  put: (path, body) => request("PUT", path, body),
  del: (path) => request("DELETE", path),
};

/** 上传文件（图片），单独走 multipart */
async function uploadImage(file) {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(API_BASE + "/upload", {
    method: "POST",
    headers: getToken() ? { Authorization: "Bearer " + getToken() } : {},
    body: form,
  });
  const data = await resp.json();
  if (!resp.ok) {
    if (resp.status === 401) {
      clearAuth();
      location.href = "login.html";
    }
    toast(data.detail || "上传失败", "error");
    throw new Error("上传失败");
  }
  return data.url;
}
