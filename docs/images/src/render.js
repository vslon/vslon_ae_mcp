// Usage: node render.js cover how-it-works   (needs Playwright; writes ../<name>.png at 2x)
const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1600,height:1000},deviceScaleFactor:2});
for(const n of process.argv.slice(2)){await p.goto('file://'+__dirname+'/'+n+'.html',{waitUntil:'networkidle'});await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(300);await p.screenshot({path:__dirname+"/../"+n+".png"});
console.log(n, await p.evaluate(()=>document.fonts.check("20px 'JetBrains Mono'")));}
await b.close();})();
