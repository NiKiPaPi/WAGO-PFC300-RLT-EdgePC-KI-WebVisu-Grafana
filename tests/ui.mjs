// Real HMI/HTTP/MQTT browser QA; Influx HTTP test double from mqtt_probe.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
const {chromium}=await import(pathToFileURL(path.join(process.env.PLAYWRIGHT_MODULE,'index.mjs')).href);
const root=process.cwd(),env=Object.fromEntries(fs.readFileSync('.env','utf8').split(/\r?\n/).filter(x=>x&&!x.startsWith('#')&&x.includes('=')).map(x=>[x.slice(0,x.indexOf('=')),x.slice(x.indexOf('=')+1)]));
const evidence={mode:'actual React HMI with loopback MQTT; Influx HTTP test double; no Grafana',checks:[],screenshots:[]};
const errors=[];let browser;const children=[];
function start(exe,args){const p=spawn(exe,args,{cwd:root,env:process.env,windowsHide:true,stdio:['ignore','pipe','pipe']});children.push(p);return p;}
async function untilReady(p,needle){return new Promise((resolve,reject)=>{let out='';const timer=setTimeout(()=>reject(new Error('Fixture readiness timeout')),65000);p.stdout.on('data',data=>{out+=data;if(out.includes(needle)){clearTimeout(timer);resolve();}});p.once('exit',code=>{clearTimeout(timer);reject(new Error('Fixture exited '+code));});});}
function check(name,condition){evidence.checks.push({name,passed:!!condition});if(!condition)throw new Error(name);}
try{
 const fixture=start(process.env.RLT_PYTHON,['-m','scripts.mqtt_probe','--serve']);await untilReady(fixture,'UI TEST FIXTURE READY');
 const vite=start(process.execPath,['frontend/node_modules/vite/bin/vite.js','frontend','--host','127.0.0.1','--port','8080','--strictPort']);await untilReady(vite,'Local:');
 browser=await chromium.launch({headless:true,...(process.env.RLT_BROWSER_PATH?{executablePath:process.env.RLT_BROWSER_PATH}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://localhost:8080');await page.locator('input[autocomplete=username]').fill('operator');await page.locator('input[autocomplete=current-password]').fill(env.INITIAL_OPERATOR_PASSWORD);await page.getByRole('button',{name:'Anmelden',exact:true}).click();
 await page.getByText('● Daten aktuell',{exact:true}).waitFor();check('operator login / fresh WebSocket',true);
 await page.getByRole('button',{name:'Außenluftklappe',exact:true}).click();await page.getByRole('dialog',{name:'Außenluftklappe',exact:true}).waitFor();check('SVG component dialog',true);await page.getByRole('button',{name:'Schließen ×',exact:true}).click();
 await page.locator('input[id="temperature.requested"]').fill('23');await page.locator('.control').filter({has:page.locator('input[id="temperature.requested"]')}).getByRole('button',{name:'Ändern',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Änderung bestätigen',exact:true});await dialog.waitFor();check('old/new/target confirmation',(await dialog.innerText()).includes('22 → 23'));
 await dialog.getByRole('button',{name:'Bestätigen',exact:true}).click();await page.getByRole('button',{name:'Bedienung',exact:true}).click();await page.getByRole('cell',{name:/temperature\.requested → 23/}).first().waitFor();await page.waitForTimeout(1200);check('command tracking visible',(await page.locator('tbody').innerText()).includes('Logik ausgeführt'));
 for(const p of ['Trends & Historie','Alarme & Ereignisse','Einstellungen','Übersicht']){await page.getByRole('button',{name:p,exact:true}).click();await page.getByRole('heading',{name:p,exact:true}).waitFor();check('navigation '+p,true);}
 for(const [name,width,height] of [['desktop',1440,1000],['tablet',820,1180],['phone',390,844]]){
   await page.setViewportSize({width,height});await page.screenshot({path:`docs/hmi-${name}.png`,fullPage:true});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);check(name+' no page overflow',!overflow);evidence.screenshots.push(`docs/hmi-${name}.png`);
   await page.getByRole('button',{name:'Bedienung',exact:true}).click();check(name+' controls visible',await page.locator('input[id="temperature.requested"]').isVisible());await page.getByRole('button',{name:'Übersicht',exact:true}).click();
 }
 await page.getByRole('button',{name:'Abmelden',exact:true}).click();await page.locator('input[autocomplete=username]').fill('viewer');await page.locator('input[autocomplete=current-password]').fill(env.INITIAL_VIEWER_PASSWORD);await page.getByRole('button',{name:'Anmelden',exact:true}).click();await page.getByText('● Daten aktuell',{exact:true}).waitFor();check('viewer controls disabled',await page.locator('input[id="temperature.requested"]').isDisabled());
 check('no JavaScript errors',errors.length===0);
 fs.writeFileSync('data/mqtt-probe/stop','stop');await page.getByText('⚠ Daten fehlen / veraltet',{exact:true}).waitFor({timeout:15000});check('communication outage warning shown',true);
}finally{
 if(browser)await browser.close();
 // fixture owns its Python children; graceful HTTP-trigger-free termination below is handled by its signal hook.
 fs.writeFileSync('data/mqtt-probe/stop','stop');
 if(children[0]?.exitCode===null)await Promise.race([new Promise(resolve=>children[0].once('exit',resolve)),new Promise(resolve=>setTimeout(resolve,10000))]);
 for(const p of children.reverse()){if(p.exitCode===null)p.kill();}
 evidence.javascript_errors=errors;fs.writeFileSync('docs/ui-results.json',JSON.stringify(evidence,null,2));
}
console.log(JSON.stringify({checks:evidence.checks.length,passed:evidence.checks.every(x=>x.passed)}));
