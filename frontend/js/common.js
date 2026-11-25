/**
 * 公共组件
 * Author: 王昱皓
 *
 * 提供：导航栏与页脚渲染、登录校验、toast 提示、价格格式化、状态标签、分页组件。
 * 每个页面引入后在 body 末尾调用 initCommon("当前页标识")。
 * 14 个页面共用同一份导航与页脚，改一处即全站生效，不要在页面里另写一份。
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
  // 重复初始化时不再插第二份导航（页面里重跑 initCommon 不会出现双导航）
  if (document.querySelector(".site-header")) return;

  const user = currentUser();
  const links = NAV_ITEMS.map(
    (it) =>
      `<a href="${it.href}" class="${it.key === activeKey ? "active" : ""}"${
        it.key === activeKey ? ' aria-current="page"' : ""
      }>${it.label}</a>`
  ).join("");

  const right = user
    ? `<a href="favorites.html" title="我的收藏">收藏</a>
       <a href="messages.html" id="nav-msg" title="消息">消息</a>
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

  // 已登录才问未读数：避免匿名访问首页时请求 401 被重定向到登录页。
  if (user) refreshUnreadBadge();
}

/**
 * 把导航「消息」的未读角标刷成真实数量。
 *
 * 原来这里写死 class="badge-dot"，红点永远亮着，用户第一天就学会忽略它；
 * 而后端 /api/messages/unread-count 一直没被调用（接口文档里列着却是死接口）。
 * 现在 0 条不显示红点，有未读才显示数字，角标才有信息量。
 */
async function refreshUnreadBadge() {
  const link = document.getElementById("nav-msg");
  if (!link || !getToken()) return;
  try {
    const { count } = await api.get("/messages/unread-count");
    const unread = Number(count) || 0;
    link.title = unread > 0 ? `消息（${unread} 条未读）` : "消息";
    link.innerHTML = unread > 0 ? `消息<span class="badge-count">${unread > 99 ? "99+" : unread}</span>` : "消息";
  } catch (err) {
    // 角标只是锦上添花，接口失败就保持无角标，不该把整页拖进错误处理
  }
}

/* ---------------- 页脚 ---------------- */

/**
 * 渲染页脚。页脚原本每个页面都没有，收口时统一由这里注入，
 * 好处是 14 个页面保持同一份信息，改课程信息只改一处。
 */
function renderFooter() {
  if (document.querySelector(".site-footer")) return;

  const footer = document.createElement("footer");
  footer.className = "site-footer";
  footer.innerHTML = `
    <div class="inner">
      <div>
        <div class="logo">闲置<span>集市</span></div>
        <p class="footer-note">校内二手交易平台 · 当面自提 · 无手续费</p>
      </div>
      <nav class="footer-links">
        <a href="goods-list.html">逛一逛</a>
        <a href="publish.html">发布闲置</a>
        <a href="my-orders.html">我的订单</a>
        <a href="favorites.html">我的收藏</a>
      </nav>
      <p class="footer-meta">《操作系统与工具链》课程项目<br>FastAPI + MySQL 8.0 + 原生 JS</p>
    </div>`;
  document.body.appendChild(footer);
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

/**
 * 绝对时间：2026-11-25T12:02:27.003782 -> 2026-11-25 12:02
 *
 * 后端直接返回 ISO 字符串，前端原来用 e(o.created_at) 原样打到页面上，
 * 用户看到的是「2026-11-25T12:02:27.003782」这种带 T 和微秒的串。
 * 订单这类需要精确时间的场景用这个，聊天用上面的相对时间。
 */
function formatTime(isoText) {
  if (!isoText) return "";
  const date = new Date(isoText);
  if (Number.isNaN(date.getTime())) return String(isoText);
  const pad = (n) => String(n).padStart(2, "0");
  return (
    date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate()) +
    " " + pad(date.getHours()) + ":" + pad(date.getMinutes())
  );
}

/** 订单状态 -> 标签样式与文案 */
const ORDER_STATUS = {
  // PENDING 是买家下单后等卖家「确认出售」，文案必须与按钮动作一致；
  // 这里原来写「待买家确认」，与 order_state.py 里卖家那一跳正好相反。
  PENDING: { text: "待卖家确认", cls: "status-pending" },
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

/** 页面初始化：注入导航与页脚、兜底图片、统一错误 */
function initCommon(activeKey) {
  renderHeader(activeKey);
  renderFooter();

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
