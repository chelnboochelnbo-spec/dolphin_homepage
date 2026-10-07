const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn,execFileSync}=require('node:child_process');
const origin=process.env.CALENDAR_BASE_URL||'http://127.0.0.1:8766';
const output=path.join(process.env.RUNNER_TEMP||process.env.TEMP||'/tmp','dolphin-calendar-previews');
// The same explicit JST date drives the Python renderer and browser clock.
// Include the original date, the first reported regression day, and a new year.
const actualToday=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const fixtureDates=[...new Set([actualToday,'2026-10-07','2026-10-27','2027-01-01'])];
(async()=>{
 fs.mkdirSync(output,{recursive:true});
 const server=process.env.CALENDAR_BASE_URL?null:spawn(process.env.PYTHON||'python',['-m','http.server','8766','--bind','127.0.0.1'],{stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<60;i++){try{if((await fetch(origin)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true,...(process.env.EDGE_PATH?{executablePath:process.env.EDGE_PATH}:{})});
  for(const fixtureDate of fixtureDates){
   const fixtureHtml=execFileSync(process.env.PYTHON||'python',['-X','utf8','tests/home_calendar_fixture.py',fixtureDate],{encoding:'utf8',maxBuffer:10*1024*1024});
   for(const width of [1440,390,320]){
   const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
   await context.addInitScript(instant=>{const OriginalDate=Date;globalThis.Date=class extends OriginalDate{constructor(...args){super(...(args.length?args:[instant]));}static now(){return new OriginalDate(instant).getTime();}};},fixtureDate+'T00:00:00+09:00');
   await context.route('**/*',route=>{
    const url=new URL(route.request().url());
    if(url.origin!==new URL(origin).origin)return route.abort();
    if(url.pathname==='/')return route.fulfill({status:200,contentType:'text/html; charset=utf-8',body:fixtureHtml});
    return route.continue();
   });
   const page=await context.newPage();await page.goto(origin,{waitUntil:'networkidle'});
   const active=()=>page.locator('.calendar-month:not([hidden])');
   assert.equal(await active().getAttribute('data-calendar-panel'),fixtureDate.slice(0,7));
   assert.equal(await active().locator('th').count(),7);
   await page.locator('[data-calendar-month="2026-10"]').click();
   assert.equal(await page.locator('[data-calendar-date="2026-10-14"]').innerText(),'14\n休業');
   const expectedOctober26=fixtureDate>'2026-10-26'?'予定の登録なし':'通常営業';
   assert((await page.locator('[data-calendar-date="2026-10-26"]').innerText()).includes(expectedOctober26));
   await page.locator('[data-calendar-month="2026-12"]').click();
   await page.locator('[data-calendar-step="1"]').click();
   assert.equal(await active().getAttribute('data-calendar-panel'),'2027-01');
   assert(!(await page.locator('[data-calendar-date="2027-01-02"]').innerText()).includes('Saturday Jam'));
   await page.locator('[data-calendar-step="-1"]').click();
   assert.equal(await active().getAttribute('data-calendar-panel'),'2026-12');
   const nov=page.locator('[data-calendar-month="2026-11"]');await nov.focus();await page.keyboard.press('Enter');
   assert.equal(await active().getAttribute('data-calendar-panel'),'2026-11');
   await page.keyboard.press('ArrowRight');assert.equal(await active().getAttribute('data-calendar-panel'),'2026-12');
   await page.keyboard.press('Home');assert(await page.locator('[data-calendar-step="-1"]').isDisabled());
   await page.keyboard.press('End');assert(await page.locator('[data-calendar-step="1"]').isDisabled());
   await page.locator('[data-calendar-today]').click();assert.equal(await active().getAttribute('data-calendar-panel'),fixtureDate.slice(0,7));
   await nov.click();
   const link=page.locator('.calendar-event[href="/events/2026-11-28_balloon-vine-trio/"]');
   await link.scrollIntoViewIfNeeded();
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.locator('#home-calendar').screenshot({path:path.join(output,`calendar-${fixtureDate}-${width}.png`)});
   await link.focus();await page.keyboard.press('Enter');await page.waitForURL('**/events/2026-11-28_balloon-vine-trio/');
   assert.equal(await page.locator('h1').innerText(),'Balloon vine Trio');
   await context.close();
   }
   console.log(`Calendar fixture ${fixtureDate}: desktop/mobile, month click, keyboard, year boundary, operating states, detail links passed.`);
  }
 }finally{await browser?.close();server?.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
