#!/usr/bin/env node
// Browser-side focused regression; never drives Orca or a physical printer.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.HELIX_REVIEW_PLAYWRIGHT || 'playwright');
const base = process.env.HELIX_REVIEW_URL;
const output = process.env.HELIX_REVIEW_OUTPUT;
const resultFile = process.env.HELIX_REVIEW_RESULT_FILE;
const mode = process.argv[2] || 'toolbar';
if (!base || !output || !resultFile || !['toolbar','native'].includes(mode)) throw Error('Set the private review URL/output/result file and choose toolbar or native');
const url = new URL(base);
if (url.protocol !== 'http:' || !/^192\.168\.\d+\.\d+$/.test(url.hostname)) throw Error('Review must use the approved private LAN surface');

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ executablePath: process.env.HELIX_REVIEW_BROWSER,
    headless: true, args: ['--no-sandbox','--disable-background-networking'] });
  const context = await browser.newContext({viewport:{width:1280,height:900}});
  await context.route('**/*', route => new URL(route.request().url()).origin === url.origin ? route.continue() : route.abort());
  const page = await context.newPage();
  const failures=[]; page.on('pageerror', error=>failures.push(error.message));
  const frames={};
  async function state(){ const r=await page.request.get(url.origin+'/api/review-state'); assert.equal(r.status(),200);return (await r.json()).state; }
  async function until(fn,description){const end=Date.now()+10000;while(Date.now()<end){if(await fn())return;await page.waitForTimeout(100)}throw Error(description);}
  async function capture(name){await page.waitForTimeout(900);const file=path.join(output,mode+'-'+name+'.png');await page.screenshot({path:file});frames[path.basename(file)]=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');}
  async function tap(x,y){const box=await page.locator('#frame').boundingBox();const response=page.waitForResponse(r=>r.url()===url.origin+'/api/tap'&&r.request().method()==='POST');await page.mouse.click(box.x+x*box.width/800,box.y+y*box.height/480);assert.equal((await response).status(),200);await page.waitForTimeout(900);}
  async function drag(x0,y0,x1,y1){const box=await page.locator('#frame').boundingBox();const response=page.waitForResponse(r=>r.url()===url.origin+'/api/drag'&&r.request().method()==='POST');await page.mouse.move(box.x+x0*box.width/800,box.y+y0*box.height/480);await page.mouse.down();await page.mouse.move(box.x+x1*box.width/800,box.y+y1*box.height/480,{steps:8});await page.mouse.up();assert.equal((await response).status(),200);await page.waitForTimeout(900);}
  async function button(action,label){const response=page.waitForResponse(r=>r.url()===url.origin+'/api/'+action&&r.request().method()==='POST');await page.getByRole('button',{name:label,exact:true}).click();assert.equal((await response).status(),200);await page.waitForTimeout(900);}
  async function status(){return page.request.get(url.origin+'/api/status').then(r=>r.json());}
  async function home(native=false){if(native)await tap(38,60);else await button('home','Home');await until(async()=>{const s=await status();return s.panel==='home'&&s.overlays.length===0},'Home must expose native Home');}
  try {
    await page.goto(base);await until(async()=>await state()===1,'A fresh received request must remain unstarted');
    assert.equal(await page.locator('#finish').isDisabled(),true);
    await capture('fresh');
    if(mode==='native'){await home(true);await capture('home-ready');await tap(500,55);assert.equal(await state(),1);}
    await tap(205,276);await until(async()=>await state()===2,'Native Start must begin only the mock');
    await until(async()=>await page.locator('#finish').isEnabled(),'Finish must immediately become available');
    const viewports=[];
    for(const width of [375,640,1280]){
      await page.setViewportSize({width,height:900});const box=await page.locator('#finish').boundingBox();
      assert(box.x>=0&&box.y>=0&&box.x+box.width<=width&&box.y+box.height<=900,'Finish must be fully visible');
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width,'No horizontal control overflow');
      viewports.push({width,finish_fully_visible:true});await capture('printing-'+width);
    }
    if(mode==='native'){
      await home(true);assert.equal(await state(),2);await capture('home-active');await tap(320,220);
      await until(async()=>(await status()).overlays.includes('print_status_panel'),'Stock Home print card must return to Print Status');await capture('return-print');
      await button('back','Back');await until(async()=>(await status()).overlays.length===0,'Back must leave Print Status');
      await tap(500,55);assert.equal(await state(),2);await capture('resume-calibration');await tap(360,320);
    }else await button('finish-mock','Finish simulated print');
    await until(async()=>await state()===3,'Finish must reach native choices promptly');await capture('choices');
    await home();assert.equal(await state(),3);await tap(500,55);
    await tap(470,280);await capture('dropdown-open');await drag(430,220,430,80);await capture('dropdown-scrolled');await tap(320,130);await tap(123,370);
    await until(async()=>await state()===4,'Native 205/Next must return a result');await capture('returned');
    const result=JSON.parse(fs.readFileSync(resultFile,'utf8')).result;
    assert.equal(result.value,205,'The visible terminal selection must actually be 205°C');
    assert.equal(result.request_id,'f4a33a9c526e24c63c2d653fc51cfb0c');
    assert.equal(result.mock_only,true);
    await home();assert.equal(await state(),4);await tap(500,55);await capture('result-resumed');
    assert.deepEqual(failures,[]);
    fs.writeFileSync(path.join(output,mode+'-report.json'),JSON.stringify({status:'pass',mode,fresh_context:true,selected_value:result.value,request_id:result.request_id,viewport_checks:viewports,frames,page_errors:failures},null,2)+'\n');
    console.log('PASS: fresh browser '+mode+' Finish, Home/Back/return, responsive controls, 205/Next/result resume');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exit(1)});
