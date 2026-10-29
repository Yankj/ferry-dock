// Optional artwork renderer; the Ferry Dock executable does not use Node.
// NODE_PATH=/tmp/ferry-dock-renderer/node_modules node brand/render-scenario.cjs
const fs = require('node:fs');
const path = require('node:path');
const { Resvg } = require('@resvg/resvg-js');
const source = fs.readFileSync(path.join(__dirname, 'scenario.svg'), 'utf8');
function png(width) {
  return new Resvg(source, {
    fitTo: { mode: 'width', value: width },
    font: { loadSystemFonts: true, defaultFontFamily: 'Helvetica' },
  }).render().asPng();
}
fs.writeFileSync(path.join(__dirname, 'scenario.png'), png(1040));
if (process.argv.includes('--qa')) {
  fs.writeFileSync('/tmp/ferry-dock-scenario-320.png', png(320));
}
console.log('Wrote brand/scenario.png');
