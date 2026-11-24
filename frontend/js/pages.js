/** Author: 王昱皓 · 静态页面交互入口，所有网络请求统一使用 api.js。 */

const PAGE = document.body.dataset.page;
const APP = document.getElementById("app");
const q = new URLSearchParams(location.search);
const e = escapeHtml;
const img = (value) => e((value || "").split(",")[0] || "");

function renderGoods(items) {
  if (!items.length) return '<div class="empty">暂无商品</div>';
  return `<div class="goods-grid">${items.map(g => `<a class="goods-card" href="goods-detail.html?id=${g.id}">
    <img class="goods-thumb" src="${img(g.images)}" alt="${e(g.title)}">
    <div class="goods-body"><div class="goods-title">${e(g.title)}</div>
    <div class="goods-meta"><span class="price">${formatPrice(g.price)}</span>
    <span class="goods-seller">${e(g.seller_name || "")}</span></div></div></a>`).join("")}</div>`;
}

function fail(message) { APP.innerHTML = `<div class="empty">${e(message)}</div>`; }
function value(id) { return document.getElementById(id).value.trim(); }
function html(title, body) { APP.innerHTML = `<h1 class="page-title">${e(title)}</h1>${body}`; }
function goto(path) { location.href = path; }

async function indexPage() {
  initCommon("index");
  APP.innerHTML = `<section class="hero panel mb-4"><div><h1>把闲置，交给需要的人</h1><p>校内二手交易 · 当面自提 · 无手续费</p></div>
    <div class="d-flex gap-2"><a class="btn-brand" href="publish.html">发布闲置</a><a class="btn-ghost" href="goods-list.html">随便逛逛</a></div></section>
    <div class="filter-bar" id="cats"></div><div class="d-flex justify-content-between align-items-center my-3"><h2 class="page-title mb-0">最新上架</h2><a href="goods-list.html">查看全部 ›</a></div><div id="items"></div>`;
  const cats = (await api.get("/categories")).items;
  document.getElementById("cats").innerHTML = `<a class="chip active" href="goods-list.html">全部分类</a>${cats.map(c => `<a class="chip" href="goods-list.html?category_id=${c.id}">${e(c.name)}</a>`).join("")}`;
  const data = await api.get("/goods?page=1&size=8&sort=newest");
  document.getElementById("items").innerHTML = renderGoods(data.items);
}

async function goodsListPage() {
  initCommon("goods-list");
  const state = {keyword:q.get("keyword")||"", category_id:q.get("category_id")||"", sort:q.get("sort")||"newest", page:Number(q.get("page"))||1, size:12};
  html("逛一逛", `<div class="panel filter-panel"><input id="keyword" class="form-control" placeholder="搜索商品" value="${e(state.keyword)}"><select id="category" class="form-select"></select><select id="sort" class="form-select"><option value="newest">最新发布</option><option value="price_asc">价格从低到高</option><option value="price_desc">价格从高到低</option><option value="hot">最多浏览</option></select><button id="search" class="btn-brand">搜索</button></div><p id="count" class="small text-muted mt-3"></p><div id="items"></div><div class="pager mt-3" id="pager"></div>`);
  const cats = (await api.get("/categories")).items;
  document.getElementById("category").innerHTML = `<option value="">全部分类</option>${cats.map(c => `<option value="${c.id}">${e(c.name)}</option>`).join("")}`;
  document.getElementById("category").value = state.category_id;
  document.getElementById("sort").value = state.sort;
  async function load() {
    const p = new URLSearchParams();
    Object.entries(state).forEach(([k,v]) => {if (k!=="size" && v) p.set(k,v);});
    history.replaceState(null,"","?"+p.toString());
    const data = await api.get("/goods?"+new URLSearchParams({...state}).toString());
    document.getElementById("count").textContent = `共 ${data.total} 件`;
    document.getElementById("items").innerHTML = renderGoods(data.items);
    renderPager(document.getElementById("pager"),state.page,Math.max(1,Math.ceil(data.total/state.size)),p=>{state.page=p;load();});
  }
  document.getElementById("search").onclick=()=>{state.keyword=value("keyword");state.category_id=value("category");state.sort=value("sort");state.page=1;load();};
  document.getElementById("keyword").onkeydown=ev=>{if(ev.key==="Enter")document.getElementById("search").click();};
  await load();
}

async function goodsDetailPage() {
  initCommon("goods-list");
  const id=Number(q.get("id")); if(!id) return fail("缺少商品编号");
  const g=await api.get("/goods/"+id), me=currentUser();
  // images 存的是逗号串，空项必须过滤：商品下架再上架会残留空串，不过滤就多出一格碎图。
  const photos=(g.images||"").split(",").filter(Boolean);
  const HOLDER="data:image/svg+xml;charset=utf-8,"+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><rect width="600" height="600" fill="#f0f1f2"/><text x="300" y="310" font-size="26" fill="#b4b2a9" text-anchor="middle">暂无图片</text></svg>');
  APP.innerHTML=`<div class="detail-layout"><div class="panel"><img id="main-photo" class="detail-photo" src="${photos[0]||HOLDER}" alt="${e(g.title)}">${photos.length>1?`<div class="d-flex align-items-center gap-2 mt-2"><div id="thumbs" class="d-flex gap-2 flex-grow-1 overflow-auto">${photos.map((src,i)=>`<img class="thumb-item border border-2 ${i===0?"border-primary":"border-transparent"}" src="${e(src)}" alt="商品图片 ${i+1}">`).join("")}</div><span id="photo-index" class="small text-muted">1 / ${photos.length}</span></div>`:""}</div>
    <div class="panel"><h1 class="page-title">${e(g.title)}</h1><div class="price price-large">${formatPrice(g.price)}</div><p class="text-muted">${e(g.category_name)} · ${g.view_count} 次浏览 · ${e(g.status)}</p><p class="description">${e(g.description)}</p><p>卖家：${e(g.seller_name)} · 信用分 ${g.seller_credit}</p><div class="d-flex flex-wrap gap-2"><button id="fav" class="btn-ghost">收藏</button><button id="chat" class="btn-ghost">联系卖家</button><button id="buy" class="btn-brand" ${g.status!=="在售"||me?.id===g.seller_id?"disabled":""}>${g.status!=="在售"?"暂不可购买":"立即购买"}</button></div></div></div>
    <section class="panel mt-4"><h2 class="page-title">商品评价</h2><div id="reviews"></div></section>`;
  // 点缩略图换主图并更新「第几张 / 共几张」，选中态借 Bootstrap 边框工具类，不新增 CSS。
  document.querySelectorAll(".thumb-item").forEach((el,i)=>el.onclick=()=>{document.getElementById("main-photo").src=photos[i];document.getElementById("photo-index").textContent=(i+1)+" / "+photos.length;document.querySelectorAll(".thumb-item").forEach((t,j)=>{t.classList.toggle("border-primary",i===j);t.classList.toggle("border-transparent",i!==j);});});
  document.getElementById("fav").onclick=async()=>{if(!requireLogin())return;await api.post("/favorites",{goods_id:id});toast("收藏成功","success");};
  document.getElementById("chat").onclick=()=>{if(requireLogin())goto(`messages.html?to=${g.seller_id}&goods_id=${id}`);};
  document.getElementById("buy").onclick=async()=>{if(!requireLogin())return;const o=await api.post("/orders",{goods_id:id});goto("order-detail.html?id="+o.id);};
  const reviews=(await api.get(`/goods/${id}/reviews`)).items;
  document.getElementById("reviews").innerHTML=reviews.length?reviews.map(r=>`<div class="border-bottom py-2"><b>${e(r.reviewer_name)}</b> <span class="price">${"★".repeat(r.rating)}</span><p>${e(r.content)}</p></div>`).join(""):'<div class="empty">暂无评价</div>';
}

async function authPage(register) {
  initCommon("");
  html(register?"注册账号":"登录",`<form class="panel form-card" id="form"><label>用户名<input class="form-control" id="username" required minlength="${register?3:1}" maxlength="50"></label>${register?'<label>昵称<input class="form-control" id="nickname" required maxlength="80"></label>':''}<label>密码<input class="form-control" id="password" type="password" required minlength="${register?6:1}"></label><button class="btn-brand w-100" type="submit">${register?"注册":"登录"}</button><p class="mt-3 mb-0">${register?'<a href="login.html">已有账号？去登录</a>':'<a href="register.html">还没有账号？去注册</a>'}</p></form>`);
  document.getElementById("form").onsubmit=async ev=>{
    ev.preventDefault();
    if(register){await api.post("/auth/register",{username:value("username"),nickname:value("nickname"),password:value("password")});toast("注册成功，请登录","success");goto("login.html");}
    else {const data=await api.post("/auth/login",{username:value("username"),password:value("password")});saveAuth(data.access_token,data.user);const redirect=q.get("redirect");goto(redirect?.startsWith("/pages/")?redirect:"index.html");}
  };
}

async function publishPage() {
  if(!requireLogin())return;initCommon("publish");
  const id=Number(q.get("id")); const g=id?await api.get("/goods/"+id):null;
  html(id?"编辑商品":"发布闲置",`<form id="form" class="panel form-card wide"><label>标题<input class="form-control" id="title" required maxlength="160" value="${e(g?.title||"")}"></label><label>分类<select class="form-select" id="category_id" required></select></label><label>价格（元）<input class="form-control" id="price" type="number" min="0.01" max="99999999.99" step="0.01" required value="${e(g?.price||"")}"></label><label>描述<textarea class="form-control" id="description" rows="5">${e(g?.description||"")}</textarea></label><label>商品图片（最多 5 张，每张不超过 5 MB）<input class="form-control" id="files" type="file" accept="image/png,image/jpeg,image/webp" multiple></label><div id="photos" class="small text-muted">${e(g?.images||"")}</div><button class="btn-brand" type="submit">保存商品</button></form>`);
  const cats=(await api.get("/categories")).items;
  document.getElementById("category_id").innerHTML=`<option value="">请选择分类</option>${cats.map(c=>`<option value="${c.id}">${e(c.name)}</option>`).join("")}`;
  if(g) document.getElementById("category_id").value=g.category_id;
  document.getElementById("form").onsubmit=async ev=>{ev.preventDefault();const files=[...document.getElementById("files").files];if(files.length>5){toast("最多上传 5 张图片","error");return;}
    const paths=files.length?await Promise.all(files.map(uploadImage)):(g?.images||"").split(",").filter(Boolean);
    const payload={title:value("title"),category_id:Number(value("category_id")),price:value("price"),description:value("description"),images:paths.join(",")};
    const result=id?await api.put("/goods/"+id,payload):await api.post("/goods",payload);goto("goods-detail.html?id="+result.id);};
}

async function profilePage() {
  if(!requireLogin())return;initCommon("");const me=await api.get("/auth/me");
  html("个人中心",`<div class="profile-grid"><form class="panel form-card wide" id="profile-form"><h2 class="page-title">个人资料</h2><p>账号：${e(me.username)}</p><label>昵称<input id="nickname" class="form-control" required value="${e(me.nickname)}"></label><label>电话<input id="phone" class="form-control" value="${e(me.phone||"")}"></label><label>头像<input id="avatar" class="form-control" type="file" accept="image/png,image/jpeg,image/webp"></label><button class="btn-brand">保存资料</button></form><form class="panel form-card" id="password-form"><h2 class="page-title">修改密码</h2><label>原密码<input id="old_password" class="form-control" type="password" required></label><label>新密码<input id="new_password" class="form-control" type="password" minlength="6" required></label><button class="btn-ghost">修改密码</button><div class="d-flex gap-3 mt-4"><a href="my-goods.html">我的商品</a><a href="favorites.html">我的收藏</a></div><button type="button" id="logout" class="btn-ghost mt-3">退出登录</button></form></div>`);
  document.getElementById("profile-form").onsubmit=async ev=>{ev.preventDefault();const file=document.getElementById("avatar").files[0];const avatar=file?await uploadImage(file):me.avatar;const user=await api.put("/users/me",{nickname:value("nickname"),phone:value("phone"),avatar});saveAuth(getToken(),user);toast("资料已保存","success");};
  document.getElementById("password-form").onsubmit=async ev=>{ev.preventDefault();await api.put("/users/me/password",{old_password:value("old_password"),new_password:value("new_password")});toast("密码已修改","success");ev.target.reset();};
  document.getElementById("logout").onclick=()=>{clearAuth();goto("index.html");};
}

async function myGoodsPage() {
  if(!requireLogin())return;initCommon("");
  // 原来固定 size=100 一次拉完，商品超过 100 件会被静默截断；改成真分页，页码写进地址栏便于分享与刷新。
  const state={page:Number(q.get("page"))||1,size:8};
  html("我的商品",`<div class="d-flex justify-content-between align-items-center mb-3"><span id="count" class="small text-muted"></span><a class="btn-brand btn-sm" href="publish.html">发布新商品</a></div><div id="items"></div><div class="pager" id="pager"></div>`);
  async function load(){
    const data=await api.get(`/users/me/goods?page=${state.page}&size=${state.size}`);
    const rows=data.items;
    // 删掉当前页最后一件后页码会越界，回退一页再查，避免停在空白页。
    if(!rows.length&&data.total>0&&state.page>1){state.page--;return load();}
    history.replaceState(null,"","?page="+state.page);
    document.getElementById("count").textContent=`共 ${data.total} 件`;
    document.getElementById("items").innerHTML=rows.length?rows.map(g=>`<div class="panel list-row"><img src="${img(g.images)}" alt=""><div class="flex-grow-1"><b>${e(g.title)}</b><p class="small text-muted mb-0">${e(g.status)} · ${formatPrice(g.price)}</p></div><a href="publish.html?id=${g.id}">编辑</a><button class="btn-ghost toggle" data-id="${g.id}" data-status="${g.status==='在售'?'已下架':'在售'}" ${g.status==='已售'?'disabled':''}>${g.status==='在售'?'下架':'上架'}</button><button class="btn-ghost remove" data-id="${g.id}" ${g.status==='已售'?'disabled':''}>删除</button></div>`).join(""):'<div class="empty">还没有发布商品，<a href="publish.html">去发布一件</a></div>';
    document.querySelectorAll(".toggle").forEach(b=>b.onclick=async()=>{await api.put(`/goods/${b.dataset.id}/status`,{status:b.dataset.status});load();});
    document.querySelectorAll(".remove").forEach(b=>b.onclick=async()=>{if(confirm("确定下架这件商品？")){await api.del(`/goods/${b.dataset.id}`);load();}});
    renderPager(document.getElementById("pager"),state.page,Math.max(1,Math.ceil(data.total/state.size)),p=>{state.page=p;load();});
  } await load();
}

function actionButtons(order){return (order.available_actions||[]).map(a=>`<button class="btn-${a.style==='danger'?'ghost':'brand'} action" data-id="${order.id}" data-status="${e(a.to_status)}">${e(a.label)}</button>`).join("");}
async function doAction(button, refresh){button.disabled=true;try{await api.put(`/orders/${button.dataset.id}/status`,{to_status:button.dataset.status});toast("操作成功","success");await refresh();}catch(err){button.disabled=false;}}
async function myOrdersPage(){if(!requireLogin())return;initCommon("my-orders");
  // 原来固定 size=100 一次拉完，订单多了会被静默截断；改为分页，角色/状态/页码都写进地址栏，
  // 刷新或从订单详情返回时仍停在原来的筛选结果上。
  const state={role:q.get("role")||"buyer",status:q.get("status")||"",page:Number(q.get("page"))||1,size:6};
  html("我的订单",`<div class="panel filter-panel"><select id="role" class="form-select"><option value="buyer">我买到的</option><option value="seller">我卖出的</option></select><select id="status" class="form-select"><option value="">全部状态</option><option value="PENDING">待确认</option><option value="PAID_PENDING">待付款</option><option value="COMPLETED">已完成</option><option value="CANCELLED">已取消</option></select><span id="count" class="small text-muted ms-auto"></span></div><div id="items"></div><div class="pager" id="pager"></div>`);
  document.getElementById("role").value=state.role;document.getElementById("status").value=state.status;
  async function load(){
    const query=new URLSearchParams({role:state.role,page:state.page,size:state.size});if(state.status)query.set("status",state.status);
    const data=await api.get("/orders?"+query.toString()),rows=data.items;
    // 翻到末页又撤掉一单时会越界，回退一页重查，避免停在空白页。
    if(!rows.length&&data.total>0&&state.page>1){state.page--;return load();}
    history.replaceState(null,"","?"+query.toString());
    document.getElementById("count").textContent=`共 ${data.total} 单`;
    document.getElementById("items").innerHTML=rows.length?rows.map(o=>`<div class="order-card"><div class="order-head"><span>订单号 ${e(o.order_no)}</span>${statusTag(o.status)}</div><div class="order-body"><img src="${img(o.goods_images)}" alt=""><div class="order-info"><h4>${e(o.goods_title)}</h4><span>${state.role==='buyer'?'卖家：'+e(o.seller_name):'买家：'+e(o.buyer_name)}</span></div><div><b class="price">${formatPrice(o.price)}</b><br><a href="order-detail.html?id=${o.id}">查看详情</a></div></div><div class="order-actions">${actionButtons(o)}${o.status==='COMPLETED'&&state.role==='buyer'&&!o.reviewed?`<a class="btn-ghost" href="review.html?id=${o.id}">评价卖家</a>`:''}${o.status==='COMPLETED'&&state.role==='buyer'&&o.reviewed?'<span class="small text-muted">已评价</span>':''}</div></div>`).join(""):'<div class="empty">暂无订单</div>';
    document.querySelectorAll(".action").forEach(b=>b.onclick=()=>doAction(b,load));
    renderPager(document.getElementById("pager"),state.page,Math.max(1,Math.ceil(data.total/state.size)),p=>{state.page=p;load();});
  }
  // 换筛选条件必须回到第 1 页，否则会落在新结果的空页上。
  document.getElementById("role").onchange=ev=>{state.role=ev.target.value;state.page=1;load();};
  document.getElementById("status").onchange=ev=>{state.status=ev.target.value;state.page=1;load();};
  await load();}

async function orderDetailPage(){if(!requireLogin())return;initCommon("my-orders");const id=Number(q.get("id"));if(!id)return fail("缺少订单编号");
  async function load(){
    const o=await api.get("/orders/"+id),me=currentUser();
    // 已完成订单的尾部按钮：买家没评过才给入口，评过就只留一个「已评价」标记。
    // 后端对重复评价会返回 400，但让用户点进去填完 200 字再被拒太不体面，前端先收口。
    const reviewBox=o.status!=="COMPLETED"?"":o.reviewed?'<span class="badge text-bg-success">已评价</span>':me?.id===o.buyer_id?`<a class="btn-brand" href="review.html?id=${o.id}">评价卖家</a>`:"";
    html("订单详情",`<div class="panel"><p>订单号：${e(o.order_no)}</p><p>商品：<a href="goods-detail.html?id=${o.goods_id}">${e(o.goods_title)}</a></p><p>金额：<b class="price">${formatPrice(o.price)}</b></p><p>状态：${statusTag(o.status)}</p><p>买家：${e(o.buyer_name)} · 卖家：${e(o.seller_name)}</p><p>创建时间：${e(o.created_at)}</p><p>完成时间：${o.finished_at?e(o.finished_at):"—"}</p><div class="d-flex gap-2 align-items-center">${actionButtons(o)}${reviewBox}</div></div>`);
    document.querySelectorAll(".action").forEach(b=>b.onclick=()=>doAction(b,load));}await load();}

async function favoritesPage(){if(!requireLogin())return;initCommon("");
  // 收藏也是会长到几百条的数据，原先 size=100 一次拉完，第 101 件起被静默丢掉，
  // 与「我的商品」是同一种坑，这里同样改成服务端真分页，页码写进地址栏便于分享/刷新。
  const state={page:Number(q.get("page"))||1,size:12};
  html("我的收藏",'<div id="items"></div><div class="pager" id="pager"></div>');
  async function load(){
    const data=await api.get(`/favorites?page=${state.page}&size=${state.size}`),rows=data.items;
    // 在末页取消最后一条收藏会导致页码越界，回退一页重查，避免停在空白页。
    if(!rows.length&&data.total>0&&state.page>1){state.page--;return load();}
    history.replaceState(null,"","?page="+state.page);
    document.getElementById("items").innerHTML=rows.length?rows.map(f=>`<div class="panel list-row"><img src="${img(f.goods.images)}" alt=""><div class="flex-grow-1"><a href="goods-detail.html?id=${f.goods.id}">${e(f.goods.title)}</a><p class="price mb-0">${formatPrice(f.goods.price)}</p></div><button class="btn-ghost remove" data-id="${f.goods.id}">取消收藏</button></div>`).join(""):'<div class="empty">还没有收藏</div>';
    document.querySelectorAll(".remove").forEach(b=>b.onclick=async()=>{await api.del("/favorites/"+b.dataset.id);toast("已取消收藏","success");load();});
    renderPager(document.getElementById("pager"),state.page,Math.max(1,Math.ceil(data.total/state.size)),p=>{state.page=p;load();});
  }
  await load();}

async function messagesPage(){if(!requireLogin())return;initCommon("messages");const me=currentUser();
  // goods_id 是商品详情页「联系卖家」带过来的上下文，只在首条消息用得上；
  // 但切换联系人时若把它丢掉，后面发出的消息就不再挂在任何商品上，所以拼 URL 时保留。
  let peer=Number(q.get("to"))||null;const goodsId=Number(q.get("goods_id"))||null;
  const peerUrl=id=>"?to="+id+(goodsId?"&goods_id="+goodsId:"");
  html("消息中心",`<div class="message-layout"><div class="panel"><h2 class="page-title">联系人</h2><div id="peers"></div></div><div class="panel"><h2 class="page-title" id="peer-title">选择联系人</h2><div id="conversation"></div><form id="message-form" class="d-flex gap-2 mt-3"><input id="content" class="form-control" placeholder="输入消息" required><button class="btn-brand">发送</button></form></div></div>`);
  // message 表没有「会话」实体，联系人只能从最近消息反推，课程规模下够用；
  // 反推窗口固定 100 条，超出的老联系人会漏，故下面按窗口大小给出提示，不假装完整。
  const recent=await api.get("/messages?size=100");
  const ids=[...new Set(recent.items.map(m=>m.sender_id===me.id?m.receiver_id:m.sender_id))];if(peer&&!ids.includes(peer))ids.unshift(peer);
  const peers=await Promise.all(ids.map(async id=>{try{return await api.get("/users/"+id);}catch{return{id,nickname:"用户 "+id};}}));
  document.getElementById("peers").innerHTML=peers.length?peers.map(u=>`<button class="chip peer${u.id===peer?' active':''}" data-id="${u.id}">${e(u.nickname)}</button>`).join(""):'<div class="empty">暂无会话</div>';
  async function load(){if(!peer){document.getElementById("conversation").innerHTML='<div class="empty">从左侧选择联系人</div>';return;}
    const u=peers.find(x=>x.id===peer);document.getElementById("peer-title").textContent=u?.nickname||"用户";
    const data=await api.get(`/messages?peer_id=${peer}&size=100`),rows=data.items.slice().reverse();
    // 接口按时间倒序只取最近一页，条数被截断时明确告知，避免用户以为历史消息丢了。
    const hint=data.total>rows.length?`<div class="empty small">仅显示最近 ${rows.length} 条，共 ${data.total} 条</div>`:"";
    document.getElementById("conversation").innerHTML=hint+(rows.length?rows.map(m=>`<div class="message ${m.sender_id===me.id?'mine':''}">${e(m.content)}<small>${e(m.created_at)}</small></div>`).join(""):'<div class="empty">还没有消息</div>');
    await api.put("/messages/read",{peer_id:peer});}
  document.querySelectorAll(".peer").forEach(b=>b.onclick=()=>{peer=Number(b.dataset.id);history.replaceState(null,"",peerUrl(peer));document.querySelectorAll(".peer").forEach(x=>x.classList.toggle("active",x===b));load();});
  document.getElementById("message-form").onsubmit=async ev=>{ev.preventDefault();if(!peer){toast("请先选择联系人","error");return;}await api.post("/messages",{receiver_id:peer,goods_id:goodsId,content:value("content")});document.getElementById("content").value="";load();};await load();}

async function reviewPage(){if(!requireLogin())return;initCommon("my-orders");const id=Number(q.get("id"));if(!id)return fail("缺少订单编号");
  const o=await api.get("/orders/"+id),me=currentUser();
  // 后端对「未完成 / 非买家 / 重复评价」分别返回 400、403、400，但那要等用户写完 200 字才报错。
  // 进页面就用同一组条件先拦一道，提示语与接口文案保持一致，避免两处说法不一。
  if(o.status!=="COMPLETED")return fail("交易完成后才能评价");
  if(me?.id!==o.buyer_id)return fail("只有买家可以评价");
  if(o.reviewed)return fail("该订单已评价");
  html("评价交易",`<form class="panel form-card" id="form"><p>商品：${e(o.goods_title)}</p><p class="small text-muted">评价对象：卖家 ${e(o.seller_name)}</p><label>评分<select id="rating" class="form-select"><option value="5">5 星 · 非常满意</option><option value="4">4 星 · 满意</option><option value="3">3 星 · 一般</option><option value="2">2 星 · 不太满意</option><option value="1">1 星 · 不满意</option></select></label><label>评价内容<textarea id="content" class="form-control" rows="5" required maxlength="2000"></textarea></label><button class="btn-brand">提交评价</button></form>`);document.getElementById("form").onsubmit=async ev=>{ev.preventDefault();await api.post(`/orders/${id}/review`,{rating:Number(value("rating")),content:value("content")});toast("评价成功","success");goto("order-detail.html?id="+id);};}

async function main(){try{switch(PAGE){case"index":return await indexPage();case"goods-list":return await goodsListPage();case"goods-detail":return await goodsDetailPage();case"login":return await authPage(false);case"register":return await authPage(true);case"publish":return await publishPage();case"profile":return await profilePage();case"my-goods":return await myGoodsPage();case"my-orders":return await myOrdersPage();case"order-detail":return await orderDetailPage();case"favorites":return await favoritesPage();case"messages":return await messagesPage();case"review":return await reviewPage();default:initCommon("");return html("页面不存在",'<div class="panel"><p>你访问的页面不存在。</p><a class="btn-brand" href="index.html">返回首页</a></div>');}}catch(err){fail(err.message||"页面加载失败");}}
main();
