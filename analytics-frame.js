(() => {
  'use strict';
  const origin='https://www.bardolphin-kanazawa.com', id='G-ZYVCESE9SD';
  if(location.origin!==origin||parent===window)return;
  let started=false;
  const categories=['home','events','artists','archive','schedule','en','zh-tw','information'];
  const names=['maps_click','schedule_click','reservation_click','phone_click'];
  window.addEventListener('message',e=>{
    if(e.origin!==origin||e.source!==parent)return;
    const v=e.data||{};
    if(v.type==='dolphin-analytics-init'&&!started&&categories.includes(v.category)){
      let choice;try{choice=JSON.parse(localStorage.getItem('dolphin-analytics-consent-v1'));}catch{return;}
      if(choice?.choice!=='granted'||choice.expires<=Date.now())return;
      started=true;window.dataLayer=[];window.gtag=function(){dataLayer.push(arguments);};
      gtag('consent','default',{analytics_storage:'granted',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'});
      gtag('set','ads_data_redaction',true);gtag('set','url_passthrough',false);gtag('js',new Date());
      gtag('config',id,{send_page_view:false,allow_google_signals:false,allow_ad_personalization_signals:false,allow_enhanced_conversions:false,cookie_domain:'www.bardolphin-kanazawa.com',cookie_expires:15552000,page_location:origin+'/'+(v.category==='home'?'':v.category+'/'),page_referrer:'',page_title:'Dolphin '+v.category});
      gtag('event','page_view');
      const script=document.createElement('script');script.async=true;script.referrerPolicy='no-referrer';script.src='https://www.googletagmanager.com/gtag/js?id='+id;document.head.append(script);
    }else if(started&&v.type==='dolphin-analytics-event'&&names.includes(v.name)){gtag('event',v.name);}
  });
})();
