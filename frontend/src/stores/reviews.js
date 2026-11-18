import {reviewsApi} from '../api/reviews.js';
/**
 * 一次查阅的快照与翻页状态都保存在本端：快照由后端留存，游标只认
 * next_cursor 顺序推进；已取过的页本地缓存，上一页不再向后端要游标。
 */
export const reviewsStore={
  session:null, pages:new Map(), cursor:0,
  reset(){this.session=null;this.pages.clear();this.cursor=0;},
  get page(){return this.pages.get(this.cursor)||null;},
  get expired(){return !!this.session && this.session.status!=='active';},
  async create(data){
    const s=await reviewsApi.create(data);
    this.reset();
    this.session=s;
    const items=s.first_page||[];
    this.pages.set(0,{cursor:0,next_cursor:items.length,items,total:s.total,page_size:s.page_size,has_next:items.length<s.total});
    return s;
  },
  async next(){
    const current=this.pages.get(this.cursor);
    const target=current.next_cursor;
    if(this.pages.has(target)){this.cursor=target;return this.pages.get(target);}
    const envelope=await reviewsApi.page(this.session.id,target);
    this.pages.set(envelope.cursor,envelope);
    this.cursor=envelope.cursor;
    return envelope;
  },
  back(){
    const keys=[...this.pages.keys()].sort((a,b)=>a-b);
    const i=keys.indexOf(this.cursor);
    if(i>0)this.cursor=keys[i-1];
  },
  async refreshStatus(){
    try{this.session=await reviewsApi.status(this.session.id);}
    catch(err){if(err.message.includes('到期')||err.message.includes('释放'))this.session={...this.session,status:'expired'};else throw err;}
    return this.session;
  },
  async close(){
    this.session=await reviewsApi.close(this.session.id);
  },
};
