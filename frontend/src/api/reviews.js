import {api} from './client.js';
export const reviewsApi={
  create:data=>api('/reviews','POST',data),
  page:(id,cursor)=>api(`/reviews/${id}/pages`,'POST',{cursor}),
  status:id=>api(`/reviews/${id}`),
  close:id=>api(`/reviews/${id}`,'DELETE'),
};
