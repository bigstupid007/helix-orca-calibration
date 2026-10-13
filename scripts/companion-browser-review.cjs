// Focused presentation proof; real Orca validation is recorded separately.
const fs=require('fs'),crypto=require('crypto'),assert=require('assert');
const {chromium}=require('/browser-runtime/node_modules/playwright');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
(async()=>{const browser=await chromium.launch({executablePath:'/ms-playwright/chromium_headless_shell-1193/chrome-linux/headless_shell',args:['--no-sandbox']});
const f=JSON.parse(fs.readFileSync('/state/fixtures.json')),html=fs.readFileSync('/state/page.html','utf8');
const report={status:'pass',kind:'companion presentation with supported-message fixtures',cases:[],frames:{}};
for(const width of [360,440,640]){const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.addInitScript(()=>{window.messages=[];window.orca={postMessage:m=>messages.push(m),onMessage:fn=>window.receive=fn};});
await page.goto('about:blank');await page.setContent(html);
await page.evaluate(s=>receive(s),f.initial);assert(await page.locator('#workflow').evaluate(e=>e.open));assert(!await page.locator('#result-card').isVisible());assert(!await page.locator('#technical').evaluate(e=>e.open));
await page.locator('#freeze').click();assert((await page.evaluate(()=>messages)).some(m=>m.command==='freeze'));
await page.evaluate(s=>receive(s),f.result);
assert.equal(await page.locator('#selected').innerText(),'205 °C');assert.equal(await page.locator('#original-effective').innerText(),'217 °C');assert.equal(await page.locator('#live-effective').innerText(),'230 °C');
assert.equal(await page.locator('#profile').innerText(),f.result.instructions.profile);assert(!await page.locator('#workflow').evaluate(e=>e.open));assert(!await page.locator('#technical').evaluate(e=>e.open));
for(const selector of ['.badge','#profile','#manual-value']){const box=await page.locator(selector).boundingBox();assert(box&&box.x>=0&&box.x+box.width<=width&&box.y>=0&&box.y+box.height<=900,selector+' visible at '+width);}
assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert((await page.locator('#selection-notice').innerText()).includes('differ'));
let name=`result-${width}.png`;await page.screenshot({path:'/state/'+name});report.frames[name]=sha('/state/'+name);
await page.locator('#technical summary').click();assert((await page.locator('#instructions').innerText()).includes('Original saved: 220 °C'));assert((await page.locator('#request').innerText()).includes(f.result.request.request_id));
await page.evaluate(s=>receive(s),{...f.result,current:{status:'unavailable'}});assert.equal(await page.locator('#live-effective').innerText(),'Unavailable');assert.equal(await page.locator('#selected').innerText(),'205 °C');
await page.evaluate(s=>receive(s),{...f.result,instructions:{...f.result.instructions,profile:'<img src=x onerror=alert(1)>'}});assert.equal(await page.locator('#profile img').count(),0);
await page.evaluate(s=>receive(s),f.initial);assert(await page.locator('#workflow').evaluate(e=>e.open));assert(!await page.locator('#result-card').isVisible());
assert.deepEqual(errors,[]);report.cases.push({width,fresh_context:true,result_first:true,instruction_visible:true,live_effective_separate:true,unavailable_preserved:true,text_escaped:true,diagnostics_retained:true,page_errors:errors});await context.close();}
fs.writeFileSync('/state/browser-report.json',JSON.stringify(report,null,2)+'\n');await browser.close();})().catch(e=>{console.error(e);process.exit(1)});
