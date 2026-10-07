const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process');
const origin=process.env.CALENDAR_BASE_URL||'http://127.0.0.1:8766';
const output=path.join(process.env.RUNNER_TEMP||process.env.TEMP||'/tmp','dolphin-calendar-previews');
(async()=>{
 fs.mkdirSync(output,{recursive:true});
 const server=process.env.CALENDAR_BASE_URL?null:spawn(process.env.PYTHON||'python',['-m','http.server','8766','--bind','127.0.0.1'],{stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<60;i++){try{if((await fetch(origin)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true,...(process.env.EDGE_PATH?{executablePath:process.env.EDGE_PATH}:{})});
  for(const width of [1440,390,320]){
   const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
   await context.addInitScript(()=>{const OriginalDate=Date;globalThis.Date=class extends OriginalDate{constructor(...args){super(...(args.length?args:['2026-10-07T00:00:00Z']));}static now(){return new OriginalDate('2026-10-07T00:00:00Z').getTime();}};});
   const page=await context.newPage();await page.goto(origin,{waitUntil:'networkidle'});
   const active=()=>page.locator('.calendar-month:not([hidden])');
   assert.equal(await active().getAttribute('data-calendar-panel'),'2026-10');
   assert.equal(await active().locator('th').count(),7);
   assert.equal(await page.locator('[data-calendar-date="2026-10-14"]').innerText(),'14\n休業');
   assert((await page.locator('[data-calendar-date="2026-10-26"]').innerText()).includes('通常営業'));
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
   await page.locator('[data-calendar-today]').click();assert.equal(await active().getAttribute('data-calendar-panel'),'2026-10');
   await nov.click();
   const link=page.locator('.calendar-event[href="/events/2026-11-28_balloon-vine-trio/"]');
   await link.scrollIntoViewIfNeeded();
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.locator('#home-calendar').screenshot({path:path.join(output,`calendar-${width}.png`)});
   await link.focus();await page.keyboard.press('Enter');await page.waitForURL('**/events/2026-11-28_balloon-vine-trio/');
   assert.equal(await page.locator('h1').innerText(),'Balloon vine Trio');
   await context.close();
  }
  console.log('Calendar: desktop/mobile, month click, keyboard, year boundary, operating states, detail links passed.');
 }finally{await browser?.close();server?.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
