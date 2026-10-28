// Optional design tooling only: NODE_PATH=/tmp/ferry-dock-renderer/node_modules node scripts/render-brand.cjs
const fs = require('node:fs');
const path = require('node:path');
const { Resvg } = require('@resvg/resvg-js');
const root = path.resolve(__dirname, '..');
let serial = 0;
function asset(file, x, y, width, height) {
  const source = fs.readFileSync(path.join(root, 'brand', file), 'utf8');
  const viewBox = source.match(/viewBox="([^"]+)"/)[1];
  const color = source.match(/ color="([^"]+)"/)?.[1] || '#142D29';
  const id = `mark-${++serial}`;
  const body = source.replace(/^<svg[^>]+>/, '').replace(/<\/svg>\s*$/, '').replaceAll('id="title"', `id="${id}"`).replaceAll('aria-labelledby="title"', `aria-labelledby="${id}"`);
  return `<svg x="${x}" y="${y}" width="${width}" height="${height}" viewBox="${viewBox}" color="${color}">${body}</svg>`;
}
const light = ['#F7F8F4', '#FFFFFF', '#142D29', '#52645E', '#0B6159', '#D6DFD8'];
const dark = ['#102321', '#17312D', '#F0F6F2', '#ADC1BA', '#76D6C6', '#35534C'];
const names = ['Canvas', 'Surface', 'Text / mark', 'Secondary', 'Accent', 'Border'];
let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1200" viewBox="0 0 1400 1200">
<rect width="1400" height="1200" fill="#F7F8F4"/>
<g font-family="PingFang SC, Heiti SC, Arial, sans-serif" fill="#142D29">
${asset('logo-light.svg', 64, 48, 32, 32)}
<text x="110" y="71" font-size="22" font-weight="600">渡口 / Ferry Dock</text>
<text x="1336" y="69" text-anchor="end" font-size="14" fill="#52645E">BRAND PREVIEW · VECTOR RENDER</text>
<path d="M64 108H1336" stroke="#D6DFD8"/>
<text x="64" y="173" font-size="15" fill="#0B6159">两岸之间 · BETWEEN TWO SHORES</text>
<text x="64" y="241" font-size="48" font-weight="600">手机上的文字，渡到电脑。</text>
<text x="64" y="282" font-size="22" fill="#52645E">A small local bridge from your phone to your computer.</text>
<rect x="64" y="334" width="636" height="300" fill="#FFFFFF" stroke="#D6DFD8"/>
<rect x="700" y="334" width="636" height="300" fill="#102321"/>
<text x="92" y="373" font-size="13" fill="#52645E">LIGHT / 暖白底</text>
<text x="728" y="373" font-size="13" fill="#ADC1BA">DARK / 深青底</text>
${asset('wordmark-light.svg', 230, 415, 304, 122)}
${asset('wordmark-dark.svg', 866, 415, 304, 122)}
<text x="92" y="599" font-size="13" fill="#52645E">16 / 24 / 32 px</text>
<text x="728" y="599" font-size="13" fill="#ADC1BA">16 / 24 / 32 px</text>
${asset('logo-light.svg', 530, 580, 16, 16)}${asset('logo-light.svg', 568, 576, 24, 24)}${asset('logo-light.svg', 614, 572, 32, 32)}
${asset('logo-dark.svg', 1166, 580, 16, 16)}${asset('logo-dark.svg', 1204, 576, 24, 24)}${asset('logo-dark.svg', 1250, 572, 32, 32)}
<text x="64" y="696" font-size="18" font-weight="600">One shape. Two shores.</text>
<text x="64" y="727" font-size="15" fill="#52645E">单色轮廓 · 两侧码头与一段渡线 · 可编辑 SVG · 无外部字体或图像服务</text>`;
for (let row = 0; row < 2; row++) {
  const palette = row ? dark : light;
  const y = 772 + row * 132;
  for (let i = 0; i < 6; i++) {
    const x = 64 + i * 216;
    svg += `<rect x="${x}" y="${y}" width="192" height="60" fill="${palette[i]}" stroke="#D6DFD8"/><text x="${x}" y="${y + 84}" font-size="13">${names[i]}</text><text x="${x}" y="${y + 105}" font-size="12" fill="#52645E">${palette[i]}</text>`;
  }
}
svg += `<path d="M64 1070H1336" stroke="#D6DFD8"/><text x="64" y="1112" font-size="16">Original geometric artwork · MIT</text><text x="1336" y="1112" text-anchor="end" font-size="15" fill="#52645E">github.com/Yankj/ferry-dock</text><text x="64" y="1151" font-size="13" fill="#52645E">This is a vector brand sheet, not a browser or real-device acceptance screenshot.</text></g></svg>`;
fs.writeFileSync(path.join(root, 'brand', 'preview.svg'), svg);
const png = new Resvg(svg, { font: { loadSystemFonts: true, defaultFontFamily: 'Heiti SC' } }).render().asPng();
fs.writeFileSync(path.join(root, 'brand', 'preview.png'), png);
console.log(`Wrote brand/preview.svg and brand/preview.png (${png.length} bytes)`);
