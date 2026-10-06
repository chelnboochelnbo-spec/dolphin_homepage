// Read-only browser QA. Never submit a reservation or contact a customer.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const origin = 'http://127.0.0.1:8765';
const out = process.env.RUNNER_TEMP ? `${process.env.RUNNER_TEMP}/dolphin-theme-previews` : '/tmp/dolphin-theme-previews';
fs.mkdirSync(out, {recursive: true});
function lum(rgb) { return rgb.map(v=>v/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0); }
function ratio(a,b) { const [lo,hi]=[lum(a),lum(b)].sort((x,y)=>x-y); return (hi+.05)/(lo+.05); }
async function checkContrast(locator, label) {
  const c=await locator.evaluate(el=>{
    const foreground=getComputedStyle(el).color.match(/[\d.]+/g).slice(0,3).map(Number);
    let n=el, background;
    while(n) {const s=getComputedStyle(n).backgroundColor.match(/[\d.]+/g).map(Number);if(s.length===3||s[3]===1){background=s.slice(0,3);break;} n=n.parentElement;}
    return {foreground,background:background||[255,255,255]};
  });
  const value=ratio(c.foreground,c.background);
  assert(value>=4.5,`${label}: insufficient contrast ${value.toFixed(2)} ${JSON.stringify(c)}`);
  return {label,ratio:Number(value.toFixed(2))};
}
(async()=>{
  const server=spawn('python',['-m','http.server','8765','--bind','127.0.0.1'],{stdio:'ignore'});
  let browser; const checks=[];
  try {
    for(let i=0;i<50;i++){try{if((await fetch(origin)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
    browser=await chromium.launch({headless:true});
    for (const width of [1440,390,320]) {
      const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
      await context.route('**/*',route=>{
        const url=new URL(route.request().url());
        if(url.origin===origin||['fonts.googleapis.com','fonts.gstatic.com'].includes(url.hostname))return route.continue();
        return route.abort();
      });
      const page=await context.newPage();
      await page.goto(origin,{waitUntil:'networkidle'});
      await page.locator('.brand-hero-logo').waitFor();
      assert(await page.locator('.brand-nav-logo').first().evaluate(el=>el.complete&&el.naturalWidth>0),'Logo failed to load');
      assert.equal(await page.locator('.hero').evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(11, 11, 11)');
      checks.push(await checkContrast(page.locator('.hero .hero-btn-primary'),`home CTA ${width}`));
      checks.push(await checkContrast(page.locator('.hero .hero-lead'),`home lead ${width}`));
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`homepage overflow ${width}`);
      if(width<1100){
        await page.locator('.menu-toggle').click();
        await page.waitForFunction(()=>{
          const box=document.querySelector('.nav-links').getBoundingClientRect();
          return box.x>=-1 && box.right<=innerWidth+1;
        });
        const box=await page.locator('.nav-links').boundingBox();
        assert(box.x>=-1&&box.x+box.width<=width+1,'Mobile navigation overflow');
        await page.locator('.menu-toggle').click();
        await page.waitForFunction(()=>document.querySelector('.nav-links').getBoundingClientRect().x>=innerWidth);
      }
      await page.evaluate(async()=>{
        await document.fonts.ready;
        await Promise.all(document.getAnimations().filter(a=>a.effect.getTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{})));
      });
      await page.screenshot({path:`${out}/home-${width}.png`});
      await page.goto(`${origin}/schedule.html`,{waitUntil:'networkidle'});
      assert.equal(await page.locator('h1').textContent(),'SCHEDULE');
      const active=page.locator('.month-link.active');
      checks.push(await checkContrast(active,`active month ${width}`));
      const card=page.locator('.lineup-month-group.active .lineup-item:not(.operating-day)').first();
      if(await card.count()){
        await card.scrollIntoViewIfNeeded();
        checks.push(await checkContrast(card.locator('.lineup-artist'),`event title ${width}`));
        await card.hover();
        checks.push(await checkContrast(card.locator('.lineup-artist'),`event hover title ${width}`));
        checks.push(await checkContrast(card.locator('.lineup-reserve-btn'),`event reserve ${width}`));
        checks.push(await checkContrast(card.locator('.weekday'),`event weekday on hover ${width}`));
      }
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`schedule overflow ${width}`);
      await page.screenshot({path:`${out}/schedule-${width}.png`});
      for(const lang of ['en','zh-tw']){
        await page.goto(`${origin}/${lang}/`,{waitUntil:'networkidle'});
        assert(await page.locator('.brand-nav-logo').first().evaluate(el=>el.complete&&el.naturalWidth>0));
        checks.push(await checkContrast(page.locator('.inbound-hero .btn.primary'),`${lang} CTA ${width}`));
        const reservationHeading=page.locator('#reservation h2').first();
        if(await reservationHeading.count()) checks.push(await checkContrast(reservationHeading,`${lang} reservation heading ${width}`));
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${lang} overflow ${width}`);
      }
      await page.goto(`${origin}/artists/`,{waitUntil:'networkidle'});
      checks.push(await checkContrast(page.locator('.artists-kicker'),`artists kicker ${width}`));
      await page.goto(`${origin}/archive/`,{waitUntil:'networkidle'});
      checks.push(await checkContrast(page.locator('.archive-kicker'),`archive kicker ${width}`));
      await context.close();
    }
    fs.writeFileSync(`${out}/checks.json`,JSON.stringify(checks,null,2));
    console.log('MONOCHROME_BROWSER_QA_PASS '+JSON.stringify(checks));
  } finally {if(browser)await browser.close(); server.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
