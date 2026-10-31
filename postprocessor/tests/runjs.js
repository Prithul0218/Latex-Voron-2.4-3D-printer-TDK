// usage: node runjs.js <html> <settings-json> <in1> [in2 ...]  -> writes out_<in>
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
(async () => {
  const [html, settingsJson, ...inputs] = process.argv.slice(2);
  const tmp = path.resolve('page_test.html');
  const src = fs.readFileSync(html, 'utf8');
  fs.writeFileSync(tmp, /^<!doctype/i.test(src) ? src : '<!doctype html><html><head><meta charset=utf8></head><body>' + src + '</body></html>');
  const b = await chromium.launch(); const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + tmp); await p.waitForTimeout(500);
  for (const f of inputs) {
    const lines = fs.readFileSync(f, 'utf8').split('\n');
    const out = await p.evaluate(([lines, s]) => {
      const o = JSON.parse(s); o.objPct = new Map();
      return window.__pp.processGcode(lines, o).out;
    }, [lines, settingsJson]);
    fs.writeFileSync('out_' + path.basename(f), out.join('\n') + '\n');
  }
  if (errs.length) console.log('PAGE ERRORS', errs);
  await b.close();
})();
