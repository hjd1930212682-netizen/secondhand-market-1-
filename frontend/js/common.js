/**
 * 公共组件
 * Author: 王昱皓
 *
 * 提供：导航栏渲染、登录校验、toast 提示、价格格式化、状态标签、分页组件。
 * 每个页面引入后在 body 末尾调用 initCommon("当前页标识")。
 */

/* ---------------- Toast ---------------- */

function toast(message, type) {
  let wrap = document.getElementById("toast-wrap");
  if (!wrap) {
    wrap = document.createElement("div");
    wrap.id = "toast-wrap";
    document.body.appendChild(wrap);
  }
  const item = document.createElement("div");
  item.className = "toast-item " + (type || "");
  item.textContent = message;
  wrap.appendChild(item);
  setTimeout(() => item.remove(), 2600);
}

/** 转义接口文本，避免商品标题等字段被当作 HTML 执行 */
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[ch]);
}

/* ---------------- 导航栏 ---------------- */

const NAV_ITEMS = [
  { key: "index", label: "首页", href: "index.html" },
  { key: "goods-list", label: "逛一逛", href: "goods-list.html" },
  { key: "publish", label: "发布闲置", href: "publish.html" },
  { key: "my-orders", label: "我的订单", href: "my-orders.html" },
  { key: "messages", label: "消息", href: "messages.html" },
];

/** 渲染顶部导航，activeKey 用于高亮当前页 */
function renderHeader(activeKey) {
  const user = currentUser();
  const links = NAV_ITEMS.map(
    (it) =>
      `<a href="${it.href}" class="${it.key === activeKey ? "active" : ""}">${it.label}</a>`
  ).join("");

  const right = user
    ? `<a href="favorites.html" title="我的收藏">收藏</a>
       <a href="messages.html" class="badge-dot" title="消息">消息</a>
       <a href="profile.html" class="d-flex align-items-center gap-2">
         <img class="avatar-mini" src="${escapeHtml(user.avatar || "")}" alt="">
         <span>${escapeHtml(user.nickname || user.username)}</span>
       </a>`
    : `<a href="login.html" class="btn-ghost btn-sm">登录</a>
       <a href="register.html" class="btn-brand btn-sm">注册</a>`;

  const header = document.createElement("header");
  header.className = "site-header";
  header.innerHTML = `
    <div class="inner">
      <a href="index.html" class="logo">闲置<span>集市</span></a>
      <nav class="nav-links">${links}</nav>
      <div class="header-search">
        <input id="navSearch" type="text" placeholder="搜索你想要的闲置好物">
      </div>
      <div class="header-actions">${right}</div>
    </div>`;
  document.body.prepend(header);

  // 导航搜索框跳转到列表页
  const box = document.getElementById("navSearch");
  if (box) {
    box.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && box.value.trim()) {
        location.href = "goods-list.html?keyword=" + encodeURIComponent(box.value.trim());
      }
    });
  }
}

/* ---------------- 登录校验 ---------------- */

/** 未登录直接跳登录页，返回当前用户 */
function requireLogin() {
  const user = currentUser();
  if (!user) {
    location.href = "login.html?redirect=" + encodeURIComponent(location.pathname);
    return null;
  }
  return user;
}

/* ---------------- 工具函数 ---------------- */

/** 金额格式化：1299 -> 1,299.00 */
function formatPrice(value) {
  const n = Number(value || 0);
  return n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** 相对时间：3 分钟前 / 2 天前 */
function timeAgo(isoText) {
  if (!isoText) return "";
  const diff = (Date.now() - new Date(isoText).getTime()) / 1000;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return Math.floor(diff / 60) + " 分钟前";
  if (diff < 86400) return Math.floor(diff / 3600) + " 小时前";
  if (diff < 2592000) return Math.floor(diff / 86400) + " 天前";
  return new Date(isoText).toLocaleDateString("zh-CN");
}

/** 订单状态 -> 标签样式与文案 */
const ORDER_STATUS = {
  PENDING: { text: "待买家确认", cls: "status-pending" },
  PAID_PENDING: { text: "待付款", cls: "status-paid" },
  COMPLETED: { text: "已完成", cls: "status-done" },
  CANCELLED: { text: "已取消", cls: "status-cancel" },
};

function statusTag(status) {
  const s = ORDER_STATUS[status] || { text: status, cls: "status-pending" };
  return `<span class="status-tag ${s.cls}">${s.text}</span>`;
}

/** 渲染分页按钮 */
function renderPager(container, page, totalPages, onChange) {
  if (!container) return;
  if (totalPages <= 1) {
    container.innerHTML = "";
    return;
  }
  const btn = (label, p, active, disabled) =>
    `<button class="${active ? "active" : ""}" ${disabled ? "disabled" : ""} data-page="${p}">${label}</button>`;

  let html = btn("上一页", page - 1, false, page <= 1);
  for (let p = 1; p <= totalPages; p++) {
    if (p === 1 || p === totalPages || Math.abs(p - page) <= 2) {
      html += btn(p, p, p === page, false);
    } else if (Math.abs(p - page) === 3) {
      html += `<button disabled>…</button>`;
    }
  }
  html += btn("下一页", page + 1, false, page >= totalPages);
  container.innerHTML = html;

  container.querySelectorAll("button[data-page]").forEach((b) => {
    b.addEventListener("click", () => {
      const p = Number(b.dataset.page);
      if (p >= 1 && p <= totalPages && p !== page) onChange(p);
    });
  });
}

/** 页面初始化：注入导航、兜底图片、统一错误 */
function initCommon(activeKey) {
  renderHeader(activeKey);

  // 图片加载失败时显示占位色块
  document.addEventListener(
    "error",
    (e) => {
      if (e.target.tagName === "IMG" && !e.target.dataset.fallback) {
        e.target.dataset.fallback = "1";
        e.target.src =
          "data:image/svg+xml;charset=utf-8," +
          encodeURIComponent(
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect width="200" height="200" fill="#f0f1f2"/><text x="100" y="105" font-size="13" fill="#b4b2a9" text-anchor="middle">暂无图片</text></svg>'
          );
      }
    },
    true
  );
}
