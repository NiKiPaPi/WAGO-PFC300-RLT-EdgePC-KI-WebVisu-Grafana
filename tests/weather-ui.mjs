import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(path.join(process.env.PLAYWRIGHT_MODULE,'index.mjs')).href);
const env=Object.fromEntries(fs.readFileSync('.env','utf8').split(/\r?\n/).filter(x=>x&&!x.startsWith('#')&&x.includes('=')).map(x=>[x.slice(0,x.indexOf('=')),x.slice(x.indexOf('=')+1)]));
const browser=await chromium.launch({headless:true,executablePath:process.env.RLT_BROWSER_PATH});
const evidence=[];
try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://localhost:8080');await page.locator('input[autocomplete=username]').fill('operator');await page.locator('input[autocomplete=current-password]').fill(env.INITIAL_OPERATOR_PASSWORD);await page.getByRole('button',{name:'Anmelden',exact:true}).click();
 const panel=page.getByRole('region',{name:'Wettervorhersage'});await panel.getByText(/Letzter erfolgreicher Abruf/).waitFor();
 if(await panel.locator('.weather-days button').count()!==7)throw Error('Seven cards missing');
 await panel.locator('.weather-days button').nth(1).click();if(await panel.locator('tbody tr').count()<23)throw Error('Hourly table missing');
 for(const [name,width,height] of [['desktop',1440,1000],['tablet',820,1180],['phone',390,844]]){
  await page.setViewportSize({width,height});await panel.scrollIntoViewIfNeeded();await page.screenshot({path:`docs/weather-${name}.png`,fullPage:true});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Overflow '+name);evidence.push({name:name+' weather layout',passed:true});
 }
 await page.getByRole('button',{name:'Abmelden',exact:true}).click();await page.locator('input[autocomplete=username]').fill('viewer');await page.locator('input[autocomplete=current-password]').fill(env.INITIAL_VIEWER_PASSWORD);await page.getByRole('button',{name:'Anmelden',exact:true}).click();await panel.getByText(/Letzter erfolgreicher Abruf/).waitFor();
 if(await panel.getByRole('button',{name:'Ort suchen',exact:true}).count())throw Error('Viewer search must be hidden');
 evidence.push({name:'Viewer displays forecast without location mutation',passed:true});if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync('docs/weather-ui-results.json',JSON.stringify({timestamp:new Date().toISOString(),checks:evidence},null,2));console.log(JSON.stringify(evidence));
}finally{await browser.close();}
