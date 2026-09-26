export function completedActivity(lane, item_id) {
  fetch('/api/child/activity', {method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json','X-Admin-Action':'1'},
    body:JSON.stringify({lane,item_id})}).catch(()=>{});
}
