import {table} from '../components/common/table.js';
import {esc} from '../utils/html.js';
import {reviewsStore} from '../stores/reviews.js';

function remainSeconds(session){
  if(!session || session.status!=='active')return 0;
  return Math.max(0,Math.ceil((new Date(session.expires_at).getTime()-Date.now())/1000));
}
function statusBadge(session){
  const map={active:['active','查阅中'],expired:['expired','已到期'],closed:['closed','已结束']};
  const [cls,text]=map[session.status]||['active',session.status];
  return `<span class="badge review-badge ${cls}">${esc(text)}</span>`;
}
function reader(){
  const s=reviewsStore.session;
  if(!s)return '<div class="empty">还没有进行中的复核查阅。在右侧发起一次查阅，系统会把当下的申请与样本量同时留存为快照。</div>';
  const page=reviewsStore.page||{items:[],cursor:0,next_cursor:0,has_next:false};
  const from=page.cursor+1,to=page.next_cursor;
  const pages=Math.max(1,Math.ceil(s.total/s.page_size));
  const currentPage=Math.floor(page.cursor/s.page_size)+1;
  const expired=reviewsStore.expired;
  return `<div class="review-card">
    <div class="section-top"><h2>${esc(s.code)}</h2>${statusBadge(s)}
      <span class="review-countdown">${s.status==='active'?`剩余 ${remainSeconds(s)} 秒 · 留存 ${s.total} 条 · 第 ${currentPage}/${pages} 页`:'留存数据已释放'}</span></div>
    ${expired?'<div class="notice review-expired">查阅已到期，旧页已拒绝访问，留存快照已释放。请重新发起一次查阅。<button id="review-new" class="link">开新查阅 ↗</button></div>':''}
    ${table(['快照位序','申请编号','接收方','移交量','快照样本量'],page.items.map(x=>[
      `<small>#${x.position}</small>`,
      `<strong>${esc(x.transfer_code)}</strong><small>${esc(x.sample_code)}</small>`,
      esc(x.destination),
      `${x.transfer_quantity} 份`,
      `<b class="quantity">${x.sample_quantity}</b> 份`]))}
    <div class="pager">
      <button id="review-back" ${page.cursor===0?'disabled':''}>← 上一页</button>
      <span>第 ${from}–${to} 条 / 共 ${s.total} 条</span>
      <button id="review-next" ${!page.has_next||expired?'disabled':''}>下一页 →</button>
    </div>
    <div class="notice">每页数据取自发起查阅那一刻的同一份快照；期间登记与改量不影响已留存页。游标顺序推进，并发翻页不漏不重。</div>
    ${s.status==='active'?'<button id="review-close" class="review-close">提前结束并释放留存</button>':''}
  </div>`;
}
export function reviewsPage(){
  const s=reviewsStore.session;
  return `<div class="split"><section><div class="section-top"><h2>移交复核查阅</h2><span>SNAPSHOT / KEYSET PAGING</span></div>${reader()}</section>
  <section class="form-panel"><span class="eyebrow">REVIEW SESSION</span><h2>发起复核查阅</h2>
  <form id="review-create-form">
    <label>查阅编号<input name="code" placeholder="review-20261118" required></label>
    <label>每页条数<input name="page_size" type="number" min="1" max="100" value="2" required></label>
    <label>留存时长（秒，留空用默认 60 秒）<input name="ttl_seconds" type="number" min="10" max="600" placeholder="60"></label>
    <button class="primary">${s?'重新发起查阅 +':'发起查阅 +'}</button>
  </form>
  <p class="help">发起时申请与样本量在同一事务、同一时刻读取并留存；闲置时不占用数据库连接，到期自动拒绝旧页并释放留存数据。</p></section></div>`;
}
