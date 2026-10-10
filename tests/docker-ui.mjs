// Browser verification against the actual Docker stack, no fixture services.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(path.join(process.env.PLAYWRIGHT_MODULE,'index.mjs')).href);
const env=Object.fromEntries(fs.readFileSync('.env','utf8').split(/\r?\n/).filter(x=>x&&!x.startsWith('#')&&x.includes('=')).map(x=>[x.slice(0,x.indexOf('=')),x.slice(x.indexOf('=')+1)]));
const evidence={mode:'real Docker HMI / Mosquitto / InfluxDB / Grafana',timestamp:new Date().toISOString(),checks:[],screenshots:[]};
const errors=[];let browser;
function check(name,ok){evidence.checks.push({name,passed:!!ok});if(!ok)throw new Error(name);}
try{
 browser=await chromium.launch({headless:true,...(process.env.RLT_BROWSER_PATH?{executablePath:process.env.RLT_BROWSER_PATH}:{})});
 const context=await browser.newContext();const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://localhost:8080');await page.locator('input[autocomplete=username]').fill('operator');await page.locator('input[autocomplete=current-password]').fill(env.INITIAL_OPERATOR_PASSWORD);await page.getByRole('button',{name:'Anmelden',exact:true}).click();await page.getByText('● Daten aktuell',{exact:true}).waitFor();
 check('operator login and fresh WebSocket',true);check('no testdouble banner',!(await page.locator('.notice').innerText()).includes('Testdouble'));
 await page.getByRole('button',{name:'Außenluftklappe',exact:true}).click();await page.getByRole('dialog',{name:'Außenluftklappe',exact:true}).waitFor();check('component details',true);await page.getByRole('button',{name:'Schließen ×',exact:true}).click();
 await page.locator('input[id="temperature.requested"]').fill('22');await page.locator('.control').filter({has:page.locator('input[id="temperature.requested"]')}).getByRole('button',{name:'Ändern',exact:true}).click();
 const confirmation=page.getByRole('dialog',{name:'Änderung bestätigen',exact:true});await confirmation.waitFor();check('confirmation target and requested value',(await confirmation.innerText()).includes('22'));await confirmation.getByRole('button',{name:'Bestätigen',exact:true}).click();
 await page.getByRole('button',{name:'Bedienung',exact:true}).click();await page.waitForTimeout(1500);check('command result visible',(await page.locator('tbody').innerText()).includes('Logik ausgeführt'));await page.getByRole('button',{name:'Übersicht',exact:true}).click();
 for(const [name,width,height] of [['desktop',1440,1000],['tablet',820,1180],['phone',390,844]]){
   await page.setViewportSize({width,height});await page.evaluate(()=>{document.activeElement?.blur();scrollTo(0,0);});await page.mouse.move(0,0);await page.screenshot({path:`docs/docker-hmi-${name}.png`,fullPage:true});evidence.screenshots.push(`docs/docker-hmi-${name}.png`);
   check(name+' page does not overflow',!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)));
   await page.getByRole('button',{name:'Bedienung',exact:true}).click();check(name+' controls visible',await page.locator('input[id="temperature.requested"]').isVisible());await page.getByRole('button',{name:'Übersicht',exact:true}).click();
 }
 await page.setViewportSize({width:1440,height:1000});await page.getByRole('button',{name:'Trends & Historie',exact:true}).click();check('at least three trend tags selected',await page.locator('.taglist input:checked').count()>=3);
 const popupWait=context.waitForEvent('page');await page.getByRole('button',{name:/Grafana-Trends öffnen/}).click();const popup=await popupWait;await popup.waitForLoadState('domcontentloaded');check('HMI opens protected Grafana link',popup.url().includes(':3000/'));await popup.close();
 const result=await context.request.post('http://localhost:3000/login',{data:{user:'admin',password:env.GRAFANA_PASSWORD}});check('Grafana authenticated login',result.ok());
 const grafana=await context.newPage();grafana.on('pageerror',e=>errors.push(e.message));await grafana.setViewportSize({width:1440,height:1000});await grafana.goto('http://localhost:3000/d/rlt/rlt-trends?from=now-1h&to=now&var-tags=temperature.supply&var-tags=temperature.accepted&var-tags=temperature.outdoor');
 await grafana.getByText('Messwerte & akzeptierte Sollwerte · Datenlücken bleiben offen',{exact:true}).waitFor({timeout:45000});await grafana.waitForTimeout(5000);
 check('Grafana rendered actual trend panel',true);check('Grafana shows three selected tags',(await grafana.locator('body').innerText()).includes('Außentemperatur'));
 check('Grafana units rendered',(await grafana.locator('body').innerText()).includes('°C'));
 await grafana.screenshot({path:'docs/docker-grafana.png',fullPage:true});evidence.screenshots.push('docs/docker-grafana.png');
 await grafana.goto('http://localhost:3000/d/rlt/rlt-trends?from=now-1h&to=now&var-tags=temperature.supply&var-tags=fan.supply.feedback&var-tags=pressure.supply');
 await grafana.getByText('Messwerte & akzeptierte Sollwerte · Datenlücken bleiben offen',{exact:true}).waitFor();await grafana.waitForTimeout(4000);
 const mixedText=await grafana.locator('body').innerText();check('mixed °C / % / Pa units rendered',mixedText.includes('°C')&&mixedText.includes('%')&&mixedText.includes('Pa'));
 await grafana.screenshot({path:'docs/docker-grafana-mixed.png',fullPage:true});evidence.screenshots.push('docs/docker-grafana-mixed.png');
 await page.getByRole('button',{name:'Abmelden',exact:true}).click();await page.locator('input[autocomplete=username]').fill('viewer');await page.locator('input[autocomplete=current-password]').fill(env.INITIAL_VIEWER_PASSWORD);await page.getByRole('button',{name:'Anmelden',exact:true}).click();await page.getByText('● Daten aktuell',{exact:true}).waitFor();await page.getByRole('button',{name:'Übersicht',exact:true}).click();check('viewer cannot edit HMI setpoints',await page.locator('input[id="temperature.requested"]').isDisabled());
 check('no uncaught JavaScript errors',errors.length===0);
}finally{if(browser)await browser.close();evidence.javascript_errors=errors;fs.writeFileSync('docs/docker-ui-results.json',JSON.stringify(evidence,null,2));}
console.log(JSON.stringify({checks:evidence.checks.length,passed:evidence.checks.every(x=>x.passed)}));
