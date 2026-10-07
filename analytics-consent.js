(() => {
  'use strict';
  if (location.origin !== 'https://www.bardolphin-kanazawa.com') return;
  const key='dolphin-analytics-consent-v1', ttl=180*86400000;
  let frame=null, granted=false;
  const en=document.documentElement.lang.startsWith('en');
  const t=en?['Site analytics','With your permission, Google Analytics uses cookies to measure visits and navigation. Form entries, phone numbers and URL query values are not sent. Advertising measurement is disabled. You can decline or withdraw at any time.','Allow analytics','Do not allow','Privacy settings','Privacy policy']:['アクセス解析の設定','同意いただいた場合のみ、Google AnalyticsのCookieを使い閲覧・ページ移動を計測します。入力内容・電話番号・URLのクエリ値は送信しません。広告目的の計測は無効です。拒否・撤回はいつでもできます。','解析に同意する','同意しない','解析の同意設定','プライバシーポリシー'];
  const css=document.createElement('link');css.rel='stylesheet';css.href='/analytics-consent.css';document.head.append(css);
  const panel=document.createElement('section');panel.id='analytics-consent';panel.setAttribute('aria-label',t[0]);
  const title=document.createElement('h2');title.textContent=t[0];
  const body=document.createElement('p');body.textContent=t[1];
  const accept=document.createElement('button');accept.type='button';accept.textContent=t[2];accept.dataset.consent='accept';
  const deny=document.createElement('button');deny.type='button';deny.textContent=t[3];deny.dataset.consent='deny';
  const policy=document.createElement('a');policy.href='/privacy.html';policy.textContent=t[5];
  panel.append(title,body,accept,deny,policy);document.body.append(panel);
  const settings=document.createElement('button');settings.type='button';settings.id='analytics-settings';settings.textContent=t[4];settings.setAttribute('aria-controls',panel.id);document.body.append(settings);
  const read=()=>{try{const v=JSON.parse(localStorage.getItem(key));return v&&v.expires>Date.now()&&['granted','denied'].includes(v.choice)?v.choice:null;}catch{return null;}};
  const category=()=>{const p=location.pathname;if(p.startsWith('/events/'))return 'events';if(p.startsWith('/artists/'))return 'artists';if(p.startsWith('/archive'))return 'archive';if(p==='/schedule.html')return 'schedule';if(p.startsWith('/en/'))return 'en';if(p.startsWith('/zh-tw/'))return 'zh-tw';return p==='/'||p==='/index.html'?'home':'information';};
  function stop(){granted=false;if(frame){try{frame.contentWindow['ga-disable-G-ZYVCESE9SD']=true;}catch{}frame.remove();frame=null;}for(const c of document.cookie.split(';')){const name=c.trim().split('=')[0];if(!/^_ga(?:_|$)/.test(name))continue;for(const domain of ['',location.hostname,'.bardolphin-kanazawa.com'])document.cookie=name+'=; Max-Age=0; Path=/; SameSite=Lax; Secure'+(domain?'; Domain='+domain:'');}}
  function start(){if(frame)return;granted=true;frame=document.createElement('iframe');frame.hidden=true;frame.title='Consent-based analytics';frame.referrerPolicy='no-referrer';frame.src='/analytics-frame.html';frame.onload=()=>{if(granted&&frame)frame.contentWindow.postMessage({type:'dolphin-analytics-init',category:category()},location.origin);};document.body.append(frame);}
  function choose(choice){try{localStorage.setItem(key,JSON.stringify({choice,expires:Date.now()+ttl}));}catch{}choice==='granted'?start():stop();panel.hidden=true;settings.focus();}
  accept.onclick=()=>choose('granted');deny.onclick=()=>choose('denied');settings.onclick=()=>{panel.hidden=false;deny.focus();};
  const initial=read();panel.hidden=!!initial;if(initial==='granted')start();else stop();
  window.addEventListener('storage',e=>{if(e.key===key||e.key===null){if(read()==='granted')start();else stop();panel.hidden=!!read();}});
  document.addEventListener('click',e=>{if(!granted||!frame)return;const a=e.target.closest('a');if(!a)return;const allowed=['maps_click','schedule_click','reservation_click','phone_click'];let name=allowed.includes(a.dataset.track)?a.dataset.track:null;if(!name&&a.protocol==='tel:')name='phone_click';if(!name&&a.hash==='#reservation')name='reservation_click';if(!name&&a.pathname==='/schedule.html')name='schedule_click';if(name)frame.contentWindow.postMessage({type:'dolphin-analytics-event',name},location.origin);});
})();
