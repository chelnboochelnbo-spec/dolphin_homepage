const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('assert/strict');
const prod='https://www.bardolphin-kanazawa.com';
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.EDGE_PATH?{executablePath:process.env.EDGE_PATH}:{})});try{
 for(const width of [1440,390]){
  const context=await browser.newContext({viewport:{width,height:900}});let google=0;
  await context.route('**/*',r=>{const u=new URL(r.request().url());if(u.hostname==='www.googletagmanager.com'){google++;return r.fulfill({contentType:'text/javascript',body:''});}if(u.origin!==prod&&u.origin!=='https://preview.vercel.app')return r.abort();let file=path.join(process.cwd(),decodeURIComponent(u.pathname));if(u.pathname.endsWith('/'))file=path.join(file,'index.html');if(!fs.existsSync(file))return r.fulfill({status:404,body:''});return r.fulfill({path:file});});
  const page=await context.newPage();await page.goto(prod+'/?email=private@example.com&phone=09012345678#secret');await page.locator('#analytics-consent').waitFor();assert.equal(google,0);
  await page.locator('[data-consent="deny"]').click();assert.equal(google,0);await page.reload();assert.equal(google,0);assert(await page.locator('#analytics-consent').isHidden());
  await page.locator('#analytics-settings').click();await page.locator('[data-consent="accept"]').click();await page.waitForFunction(()=>document.querySelector('iframe[title="Consent-based analytics"]')?.contentWindow.dataLayer?.length>0);
  const frame=page.frames().find(f=>f.url().includes('analytics-frame.html'));const commands=await frame.evaluate(()=>dataLayer.map(x=>Array.from(x)));const config=commands.find(x=>x[0]==='config')[2];assert.equal(config.page_location,prod+'/');assert.equal(config.page_referrer,'');assert.equal(config.allow_google_signals,false);assert.equal(config.allow_ad_personalization_signals,false);assert.equal(config.send_page_view,false);assert(!JSON.stringify(commands).includes('private@example.com'));assert(!JSON.stringify(commands).includes('09012345678'));
  assert.deepEqual(commands.find(x=>x[0]==='consent')[2],{analytics_storage:'granted',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'});
  await page.evaluate(()=>document.cookie='_ga=qa;path=/;secure');await page.locator('#analytics-settings').click();await page.locator('[data-consent="deny"]').click();assert.equal(page.frames().filter(f=>f.url().includes("analytics-frame.html")).length,0);assert(!(await context.cookies()).some(c=>c.name==='_ga'));const count=google;await page.reload();assert.equal(google,count);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.goto('https://preview.vercel.app/');assert.equal(await page.locator('#analytics-settings').count(),0);assert.equal(google,count);
  await page.goto(prod+'/analytics-frame.html');assert.equal(google,count);await context.close();
 }
 console.log('Consent QA passed: zero tags before consent/after refusal/on preview/direct frame; sanitized payload; ads denied; withdrawal removes frame and GA cookies; desktop/mobile.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
