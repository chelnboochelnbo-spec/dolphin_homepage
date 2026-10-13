// Local read-only UI checks. Test identity is TEST; never submit the contact form.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const origin = 'http://127.0.0.1:8768';
const out = `${process.env.RUNNER_TEMP || '/tmp'}/dolphin-inbound-previews`;
fs.mkdirSync(out, { recursive: true });
(async () => {
  const server = spawn('python', ['-m','http.server','8768','--bind','127.0.0.1'], {stdio:'ignore'});
  let browser;
  try {
    for(let i=0;i<50;i++){try{if((await fetch(origin)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
    browser = await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {})});
    for(const width of [1440,390,320]) {
      const context = await browser.newContext({viewport:{width,height:1000}, timezoneId:'America/Los_Angeles', reducedMotion:'reduce'});
      await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
      const page = await context.newPage(); const errors=[]; page.on('pageerror', e => errors.push(e.message));
      await page.clock.install({time:new Date('2026-10-13T03:00:00Z')});
      await page.goto(origin+'/en/', {waitUntil:'networkidle'});
      await page.waitForFunction(() => document.querySelector('#englishWeek').getAttribute('aria-busy')==='false');
      assert.equal(await page.locator('#englishWeek > article').count(),7);
      assert.match(await page.locator('#englishWeek > article').first().innerText(),/Tonight.*Tue,? 13 Oct 2026/);
      assert.match(await page.locator('#englishWeek [data-date="2026-10-13"]').innerText(),/LIVE & JAM[\s\S]*Doors 19:30 \/ Starts 20:00[\s\S]*¥4,500/);
      assert.match(await page.locator('#englishWeek [data-date="2026-10-14"]').innerText(),/CLOSED/);
      assert.match(await page.locator('#englishWeek [data-date="2026-10-17"]').innerText(),/JAM[\s\S]*¥2,000 \+ 2-drink minimum/);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`overflow at ${width}`);
      assert(await page.locator('.brand-hero-logo').evaluate(el=>el.complete&&el.naturalWidth>0));
      await page.screenshot({path:`${out}/english-${width}.png`,fullPage:false});
      await page.locator('#tonight').screenshot({path:`${out}/tonight-${width}.png`});
      assert.equal(await page.locator('#englishWeek [data-date="2026-10-17"] a').filter({hasText:'Event details'}).getAttribute('href'), '/events/2026-10-17_legacy-24ea07afe6/');
      await page.locator('#englishWeek [data-date="2026-10-17"] a').filter({hasText:'Request a reservation'}).click();
      assert.equal(await page.locator('#event').inputValue(),'2026-10-17_legacy-24ea07afe6');
      assert.equal(await page.locator('#date').inputValue(),'2026-10-17');
      assert.match(await page.locator('#reservationFees').innerText(),/2-drink minimum/);
      await page.goBack(); assert.equal(await page.locator('#event').inputValue(),'');
      await page.goForward(); assert.equal(await page.locator('#event').inputValue(),'2026-10-17_legacy-24ea07afe6');
      const length=await page.evaluate(()=>history.length);
      await page.locator('#englishWeek [data-date="2026-10-17"] a').filter({hasText:'Request a reservation'}).click();
      assert.equal(await page.evaluate(()=>history.length),length,'Repeated request link adds duplicate history');
      await page.selectOption('#event','2026-10-22_legacy-a52e331b05');
      assert.match(await page.locator('#reservationFees').innerText(),/Students ¥1,000 1-drink minimum/);
      await page.locator('.english-reservation').screenshot({path:`${out}/fees-${width}.png`});
      assert.equal(await page.locator('#reserveForm').count(),0,'English page must use the real web form');
      const formURL = new URL(await page.locator('#openReservationForm').getAttribute('href'));
      assert.equal(formURL.hostname,'docs.google.com');
      assert.equal(formURL.searchParams.get('entry.1102411826'),'Kiraku Jam');
      assert.equal(formURL.searchParams.get('entry.1475276432'),'2026-10-22');
      assert.equal(await page.locator('#reservationFrame').getAttribute('title'),'Dolphin reservation request form');
      await page.selectOption('#event','Normal'); assert.match(await page.locator('#reservationFees').innerText(),/¥500/);
      assert.equal(await page.locator('#date').inputValue(),'');
      // A kept-open page changes calendar date in JST, independently of visitor timezone.
      await page.clock.setSystemTime(new Date('2026-10-13T14:59:50Z'));
      await page.clock.runFor(61000);
      await page.waitForFunction(()=>document.querySelector('#englishWeek > article').dataset.date==='2026-10-14');
      assert.match(await page.locator('#englishWeek > article').first().innerText(),/CLOSED/);
      assert.equal(await page.locator('#event').inputValue(),'Normal');
      assert.deepEqual(errors,[]); await context.close();
    }
    for(const failed of ['events','operations','publication_tombstones']) {
      const context = await browser.newContext();
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if(url.pathname===`/data/${failed}.json`) return route.fulfill({status:503,body:'Unavailable'});
        return url.origin===origin ? route.continue() : route.abort();
      });
      const page = await context.newPage();
      await page.clock.install({time:new Date('2026-10-13T03:00:00Z')});
      await page.goto(origin+'/en/',{waitUntil:'networkidle'});
      await page.waitForFunction(()=>document.querySelector('#englishWeek').getAttribute('aria-busy')==='false');
      assert.equal(await page.locator('#englishWeek [data-state="unknown"]').count(),7);
      assert.equal(await page.locator('#englishWeek [data-state="bar"]').count(),0);
      if(failed!=='operations') assert.match(await page.locator('#englishEvents').innerText(),/could not be loaded/);
      await page.selectOption('#event','Normal');
      await context.close();
    }
    // A stalled operations response must stop loading after the bounded timeout.
    {
      const context = await browser.newContext();
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if(url.pathname==='/data/operations.json') return; // Hold without fulfilling.
        return url.origin===origin ? route.continue() : route.abort();
      });
      const page = await context.newPage();
      await page.clock.install({time:new Date('2026-10-13T03:00:00Z')});
      await page.goto(origin+'/en/',{waitUntil:'domcontentloaded'});
      await page.clock.runFor(11000);
      await page.waitForFunction(()=>document.querySelector('#englishWeek').getAttribute('aria-busy')==='false');
      assert.equal(await page.locator('#englishWeek [data-state="unknown"]').count(),7);
      assert(await page.locator('#event option').count()>2,'A stalled operations read hid loaded events');
      await context.close();
    }
    // Preserve a newer user choice made while a midnight refresh is pending.
    {
      const context = await browser.newContext(); let reads=0, pending;
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if(url.pathname==='/data/operations.json' && ++reads>1) { pending=route; return; }
        return url.origin===origin ? route.continue() : route.abort();
      });
      const page = await context.newPage();
      await page.clock.install({time:new Date('2026-10-13T03:00:00Z')});
      await page.goto(origin+'/en/?event_id=not-a-real-TEST-event',{waitUntil:'networkidle'});
      assert.match(await page.locator('#reservationStatus').innerText(),/unavailable/);
      await page.selectOption('#event','2026-10-15_stakes-is-high');
      await page.clock.setSystemTime(new Date('2026-10-14T03:00:00Z'));
      await page.clock.runFor(60001);
      assert(pending,'No midnight refresh was triggered');
      await page.selectOption('#event','2026-10-22_legacy-a52e331b05');
      await pending.fulfill({status:200,contentType:'application/json',body:fs.readFileSync('data/operations.json','utf8')});
      await page.waitForFunction(()=>document.querySelector('#englishWeek > article').dataset.date==='2026-10-14');
      assert.equal(await page.locator('#event').inputValue(),'2026-10-22_legacy-a52e331b05');
      assert.match(await page.locator('#reservationFees').innerText(),/Students ¥1,000 1-drink minimum/);
      await context.close();
    }
    console.log('PASS: desktop/mobile, JST rollover, fees, navigation, public-event Google Form prefill and safe fetch failures; no form submitted.');
  } finally { if(browser) await browser.close(); server.kill(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
