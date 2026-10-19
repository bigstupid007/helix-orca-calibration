#!/usr/bin/env node
/*
 * Independent 800x480 native parameter acceptance driver.
 *
 * Every UI mutation originates as a browser mouse gesture on the native frame
 * (or the viewer's native Home/Back buttons). Read-only HTTP endpoints expose
 * geometry, subjects, current navigation, and the persisted request trace.
 * This driver has no printer action, prepared-job fixture, or direct native
 * subject mutation path.
 */
'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.HELIX_REVIEW_PLAYWRIGHT || 'playwright');

const base = process.env.HELIX_REVIEW_URL;
const output = process.env.HELIX_REVIEW_OUTPUT;
const browserExecutable = process.env.HELIX_REVIEW_BROWSER;
if (!base || !output || !browserExecutable)
  throw Error('Set HELIX_REVIEW_URL, HELIX_REVIEW_OUTPUT, and HELIX_REVIEW_BROWSER');
const origin = new URL(base);
if (origin.protocol !== 'http:' || origin.hostname !== '192.168.1.114' || origin.port !== '8540')
  throw Error('Parameter acceptance is restricted to the approved private viewer at 192.168.1.114:8540');
if (!path.isAbsolute(output) || !path.isAbsolute(browserExecutable))
  throw Error('Output and browser paths must be absolute');

const VIEWPORT = { width: 800, height: 480 };
const CASES = [
  {kind:'temperature', values:{start:235,end:195,step:5,scale:false}},
  {kind:'flow_ratio_yolo', values:{pass:2}},
  {kind:'pressure_advance_pattern', values:{start:0.01,end:0.09,step:0.01}},
  {kind:'retraction', values:{start:0.2,end:2.2,step:0.2}},
  {kind:'max_volumetric_speed', values:{start:6,end:21,step:0.75}},
];

function requireCondition(value, message) { if (!value) throw Error(message); }
function sha256(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  return '{' + Object.keys(value).sort().map(key => JSON.stringify(key)+':'+canonical(value[key])).join(',') + '}';
}
function digest(value) { return sha256(Buffer.from(canonical(value))); }
function same(actual, expected, label) { assert.deepStrictEqual(actual, expected, label); }
function subjectName(kind, key) { return `orcacal__v1_${kind}_${key}_value`; }
function widgetName(kind, key) { return `orcacal__v1_${kind}_${key}`; }

(async () => {
  fs.mkdirSync(output, {recursive:true, mode:0o700});
  const browser = await chromium.launch({
    executablePath: browserExecutable,
    headless: true,
    args: ['--no-sandbox','--disable-background-networking'],
  });
  const context = await browser.newContext({viewport:{width:1100,height:900}});
  await context.route('**/*', route => {
    let requested;
    try { requested = new URL(route.request().url()); }
    catch (_) { return route.abort(); }
    return requested.origin === origin.origin ? route.continue() : route.abort();
  });
  const page = await context.newPage();
  const pageErrors=[];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('requestfailed', request => {
    const requested=new URL(request.url()); const failure=request.failure()?.errorText || '';
    if (requested.origin === origin.origin && !(requested.pathname==='/frame.png' && failure==='net::ERR_ABORTED'))
      pageErrors.push(`request failed: ${request.url()} ${failure}`);
  });
  const actions=[];
  const screenshots=[];
  const proofs=[];

  async function getJSON(route) {
    const response = await page.request.get(origin.origin+route);
    const text = await response.text();
    requireCondition(response.status() === 200, `${route} returned ${response.status()}: ${text.slice(0,300)}`);
    return JSON.parse(text);
  }
  async function until(fn, description, milliseconds=12000) {
    const end=Date.now()+milliseconds; let last;
    while (Date.now()<end) {
      try { last=await fn(); if (last) return last; } catch (error) { last=error; }
      await page.waitForTimeout(100);
    }
    throw Error(`${description}; last=${last instanceof Error ? last.message : JSON.stringify(last)}`);
  }
  async function nav() { return getJSON('/api/status'); }
  async function parameterState() { return getJSON('/api/parameter-state'); }
  async function subject(name) {
    requireCondition(/^orcacal__v1_[a-z0-9_]+$/.test(name), `Unsafe subject name: ${name}`);
    return (await getJSON('/api/subject?name='+encodeURIComponent(name))).value;
  }
  async function rawGeometry(name) {
    requireCondition(/^orcacal__[a-z0-9_]+$/.test(name), `Unsafe widget name: ${name}`);
    const raw=await getJSON('/api/geometry?name='+encodeURIComponent(name));
    requireCondition(raw && Array.isArray(raw.widgets), `Malformed geometry for ${name}`);
    const widget=raw.widgets.find(item => item && item.name===name);
    requireCondition(widget, `Native widget not found: ${name}`);
    return {raw,widget};
  }
  function visible(widget) {
    const x=Number(widget.x),y=Number(widget.y),w=Number(widget.w),h=Number(widget.h);
    return widget.hidden!==true && Number.isFinite(x) && Number.isFinite(y) &&
      Number.isFinite(w) && Number.isFinite(h) && w>0 && h>0 && x>=0 &&
      x+w<=VIEWPORT.width && y>=70 && y+h<=VIEWPORT.height;
  }
  async function frameBox() {
    const box=await page.locator('#frame').boundingBox();
    requireCondition(box && box.width>0 && box.height>0, 'Native frame is unavailable');
    return box;
  }
  async function freshFrame(previous) {
    await page.waitForFunction(old => {
      const image=document.querySelector('#frame');
      return image && image.src!==old && image.complete && image.naturalWidth===800 && image.naturalHeight===480;
    }, previous, {timeout:5000});
  }
  async function browserDrag(x0,y0,x1,y1,reason) {
    const box=await frameBox();
    const response=page.waitForResponse(r => r.url()===origin.origin+'/api/drag' && r.request().method()==='POST');
    await page.mouse.move(box.x+x0*box.width/800,box.y+y0*box.height/480);
    await page.mouse.down();
    await page.mouse.move(box.x+x1*box.width/800,box.y+y1*box.height/480,{steps:8});
    await page.mouse.up();
    const result=await response; assert.equal(result.status(),200,`Native drag failed for ${reason}`);
    const after=await page.locator('#frame').evaluate(node=>node.src);
    await freshFrame(after); actions.push({type:'browser-native-drag',reason,x0,y0,x1,y1});
  }
  async function ensureVisible(name) {
    const deadline=Date.now()+6000; let signature=null; let stable=0;
    while (Date.now()<deadline) {
      const {widget}=await rawGeometry(name);
      if (visible(widget)) {
        const next=canonical({x:widget.x,y:widget.y,w:widget.w,h:widget.h});
        if (next===signature) stable+=1; else {signature=next;stable=1;}
        if (stable===3) return widget;
        await page.waitForTimeout(200); continue;
      }
      signature=null;stable=0;
      const y=Number(widget.y),h=Number(widget.h);
      if (Number.isFinite(y) && y+h>VIEWPORT.height) await browserDrag(400,410,400,115,`reveal ${name}`);
      else if (Number.isFinite(y) && y<70) await browserDrag(400,115,400,410,`reveal ${name}`);
      else await browserDrag(400,410,400,115,`search ${name}`);
    }
    throw Error(`Could not reveal native widget ${name} using browser drag`);
  }
  async function tapWidget(name) {
    const widget=await ensureVisible(name);
    const x=Math.floor(Number(widget.x)+Number(widget.w)/2);
    const y=Math.floor(Number(widget.y)+Number(widget.h)/2);
    const box=await frameBox();
    const response=page.waitForResponse(r => r.url()===origin.origin+'/api/tap' && r.request().method()==='POST');
    await page.mouse.click(box.x+x*box.width/800,box.y+y*box.height/480);
    const result=await response; assert.equal(result.status(),200,`Native tap failed for ${name}`);
    const after=await page.locator('#frame').evaluate(node=>node.src);
    await freshFrame(after); actions.push({type:'browser-native-tap',widget:name,geometry:{x:widget.x,y:widget.y,w:widget.w,h:widget.h},x,y});
  }
  async function navButton(label, endpoint) {
    const response=page.waitForResponse(r => r.url()===origin.origin+endpoint && r.request().method()==='POST');
    await page.getByRole('button',{name:label,exact:true}).click();
    const result=await response; assert.equal(result.status(),200,`${label} navigation failed`);
    const after=await page.locator('#frame').evaluate(node=>node.src);
    await freshFrame(after); actions.push({type:'browser-native-navigation',action:label});
  }
  async function capture(name) {
    await until(async()=>{
      const image=page.locator('#frame');
      return await image.evaluate(node=>node.complete&&node.naturalWidth===800&&node.naturalHeight===480);
    },'Native frame did not settle');
    const target=path.join(output,name+'.png');
    await page.screenshot({path:target});
    screenshots.push({name:path.basename(target),sha256:sha256(fs.readFileSync(target))});
  }
  async function overlaysEndWith(name) {
    const value=await nav(); const overlays=value.overlays||[];
    return overlays[overlays.length-1]===name ? value : false;
  }
  async function openWizard() {
    await navButton('Home','/api/home');
    await until(async()=>{const n=await nav();return n.panel==='home'&&(n.overlays||[]).length===0;},'Home did not clear overlays');
    await tapWidget('orcacal__tile');
    await until(()=>overlaysEndWith('orcacal__wizard'),'Calibration chooser did not open');
  }
  async function returnToWizard() {
    for (let count=0;count<5;count++) {
      const value=await nav(), overlays=value.overlays||[];
      if (overlays[overlays.length-1]==='orcacal__wizard') return;
      if (!overlays.length) { await tapWidget('orcacal__tile'); continue; }
      await navButton('Back','/api/back');
    }
    throw Error('Could not return to the native calibration chooser');
  }
  async function openCalibration(kind) {
    await returnToWizard();
    await tapWidget(`orcacal__v1_choose_${kind}`);
    await until(()=>overlaysEndWith(`orcacal__v1_${kind}`),`${kind} setup did not open`);
  }
  async function keypadText(text) {
    await tapWidget('orcacal__v1_key_clear');
    for (const character of text) {
      const suffix=character==='.'?'dot':character;
      requireCondition(/^(dot|[0-9])$/.test(suffix),`Unsupported keypad character ${character}`);
      await tapWidget(`orcacal__v1_key_${suffix}`);
    }
  }
  async function editNumber(kind,key,value,{invalid}={}) {
    const field=subjectName(kind,key);
    await tapWidget(widgetName(kind,key));
    await until(()=>overlaysEndWith('orcacal__v1_keypad'),`${kind}.${key} keypad did not open`);
    if (invalid!==undefined) {
      const prior=await subject(field);
      await keypadText(String(invalid)); await tapWidget('orcacal__v1_key_set');
      await until(()=>overlaysEndWith('orcacal__v1_keypad'),`${kind}.${key} invalid input unexpectedly closed keypad`);
      assert.equal(await subject(field),prior,`${kind}.${key} invalid input replaced prior value`);
      const error=await subject('orcacal__v1_keypad_error');
      requireCondition(typeof error==='string'&&error.length>0,`${kind}.${key} invalid input has no visible correction`);
      actions.push({type:'invalid-input-preserved',field:`${kind}.${key}`,attempt:String(invalid),prior,error});
      await capture(`${kind}-${key}-invalid`);
    }
    await keypadText(String(value)); await tapWidget('orcacal__v1_key_set');
    await until(async()=>!(await nav()).overlays.includes('orcacal__v1_keypad'),`${kind}.${key} keypad did not commit`);
    assert.equal(String(await subject(field)),String(value),`${kind}.${key} displayed value differs`);
  }
  async function assertSubjects(kind,values) {
    for (const [key,value] of Object.entries(values)) {
      const expected=kind==='flow_ratio_yolo'&&key==='pass'?(value===1?'Recommended':'Perfectionist'):
        typeof value==='boolean'?(value?'On':'Off'):String(value);
      assert.equal(String(await subject(subjectName(kind,key))),expected,`${kind}.${key} subject mismatch`);
    }
  }
  async function generateAndProve(kind,expected,availability) {
    await tapWidget(`orcacal__v1_generate_${kind}`);
    const state=await until(async()=>{
      const candidate=await parameterState();
      const trace=candidate.trace;
      return trace&&trace.native_request&&trace.native_request.calibration===kind&&trace.phase==='blocked'&&
        candidate.native&&candidate.native.phase==='blocked'&&candidate.native.request&&
        canonical(candidate.native.request)===canonical(trace.native_request)?candidate:false;
    },`${kind} did not reach a genuine blocked Coordinator journal`,15000);
    const trace=state.trace,request=trace.native_request;
    same(request.parameters,expected,`${kind} request parameters changed`);
    same(trace.transport_request,request,`${kind} offline transport changed the request`);
    same(trace.coordinator_request,request,`${kind} Coordinator journal changed the request`);
    same(state.native.request,request,`${kind} retained native request differs`);
    const independent=digest(request);
    assert.equal(trace.native_sha256,independent,`${kind} native digest mismatch`);
    assert.equal(trace.transport_sha256,independent,`${kind} offline transport digest mismatch`);
    assert.equal(trace.coordinator_sha256,independent,`${kind} Coordinator digest mismatch`);
    assert.equal(trace.generator_dispatched,false,`${kind} unavailable route dispatched a generator`);
    assert.equal(trace.physical_adapter_enabled,false,`${kind} enabled a physical adapter`);
    assert.equal(trace.prepared,null,`${kind} created a prepared object despite unavailable route`);
    assert.equal(state.native.phase,'blocked',`${kind} native state did not retain blocker`);
    requireCondition(!state.native.prepared&&!state.native.intent&&!state.native.result&&!state.native.receipt,`${kind} unlocked a downstream action`);
    const reason=String(availability).replace(/^Blocked ·\s*/,'');
    assert.equal(trace.message,reason,`${kind} blocker differs from the offered capability reason`);
    proofs.push({kind,request_id:request.request_id,parameters:request.parameters,request_sha256:independent,
      native_request:trace.native_request,transport_request:trace.transport_request,coordinator_request:trace.coordinator_request,
      native_sha256:trace.native_sha256,transport_sha256:trace.transport_sha256,coordinator_sha256:trace.coordinator_sha256,
      phase:trace.phase,message:trace.message,generator_dispatched:false,prepared:null,physical_adapter_enabled:false});
    await capture(`${kind}-blocked`);
    await page.waitForTimeout(750); // let the real loop archive and publish the next single-use offer
  }

  try {
    await page.goto(base,{waitUntil:'domcontentloaded'});
    await until(async()=>await page.locator('#frame').evaluate(node=>node.complete&&node.naturalWidth===800&&node.naturalHeight===480),'Initial native frame unavailable');
    const health=await getJSON('/health');
    await openWizard(); await capture('00-chooser');

    for (const entry of CASES) {
      const {kind,values}=entry; await openCalibration(kind);
      const availability=await until(async()=>{
        const value=await subject(`orcacal__v1_availability_${kind}`);
        return /^Blocked ·\s*\S/.test(String(value))?value:false;
      },`${kind} must expose its genuine unavailable capability`);

      if (kind==='temperature') {
        await editNumber(kind,'start',values.start);
        await editNumber(kind,'end',values.end);
        assert.equal(await subject(subjectName(kind,'scale')),'On','Temperature Scale did not start at true');
        await tapWidget(widgetName(kind,'scale'));
        assert.equal(await subject(subjectName(kind,'scale')),'Off','Temperature Scale did not change true to false');
      } else if (kind==='flow_ratio_yolo') {
        assert.equal(await subject(subjectName(kind,'pass')),'Recommended','Flow did not start in Recommended');
        await tapWidget('orcacal__v1_flow_perfectionist');
        assert.equal(await subject(subjectName(kind,'pass')),'Perfectionist','Flow did not change to Perfectionist');
        const samples=String(await subject('orcacal__v1_flow_samples'));
        requireCondition(samples.includes('-0.04')&&samples.includes('+0.035')&&samples.includes('0.005')&&/16\s+samples/i.test(samples),
          `Perfectionist must visibly state its 16 exact additive samples: ${samples}`);
      } else if (kind==='pressure_advance_pattern') {
        requireCondition(/Direct Drive/.test(String(await subject('orcacal__v1_pa_defaults_note'))),'PA effective Direct Drive context is not visible');
        await tapWidget('orcacal__v1_pa_direct_drive');
        await assertSubjects(kind,{start:0,end:0.08,step:0.005});
        actions.push({type:'pa-defaults',selected:'direct_drive',values:{start:0,end:0.08,step:0.005}});
        await capture('pressure_advance_pattern-direct-defaults');
        await tapWidget('orcacal__v1_pa_bowden');
        await assertSubjects(kind,{start:0,end:1,step:0.05});
        actions.push({type:'pa-defaults',selected:'bowden',values:{start:0,end:1,step:0.05}});
        await capture('pressure_advance_pattern-bowden-defaults');
        await editNumber(kind,'start',values.start);
        await editNumber(kind,'end',values.end);
        await editNumber(kind,'step',values.step);
      } else {
        await editNumber(kind,'start',values.start,{invalid:kind==='retraction'?99:undefined});
        await editNumber(kind,'end',values.end);
        await editNumber(kind,'step',values.step);
      }
      await assertSubjects(kind,values); await capture(`${kind}-configured`);
      await generateAndProve(kind,values,availability);
      if (entry!==CASES[CASES.length-1]) await returnToWizard();
    }

    assert.equal(new Set(proofs.map(item=>item.request_id)).size,CASES.length,'Each calibration needs a fresh single-use request identity');
    same(pageErrors,[],'Browser page/network errors occurred');
    const report={schema:'helix-orca-v1-parameter-operator/v1',passed:true,viewport:'800x480',
      source:'actual browser pointer/drag/keypad to native Helix; real offline Coordinator and routing; unavailable generators undispatched',
      health,physical_actions:false,profile_writeback:false,prepared_fixtures:false,
      values:Object.fromEntries(CASES.map(item=>[item.kind,item.values])),proofs,actions,screenshots,page_errors:pageErrors,
      driver_sha256:sha256(fs.readFileSync(__filename)),browser_version:browser.version()};
    fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n',{mode:0o600});
    console.log(`PASS: five native parameter requests retained unchanged; report ${path.join(output,'report.json')}`);
  } finally {
    await browser.close();
  }
})().catch(error=>{console.error(error.stack||error);process.exit(1);});
