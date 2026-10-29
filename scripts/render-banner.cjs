// Optional artwork rendering; the Go transfer executable does not use Node.
// NODE_PATH=/tmp/ferry-dock-renderer/node_modules node scripts/render-banner.cjs
const fs = require('node:fs');
const path = require('node:path');
const { Resvg } = require('@resvg/resvg-js');
const root = path.resolve(__dirname, '..');

function mark(file, x, y, size, id) {
  const source = fs.readFileSync(path.join(root, 'brand', file), 'utf8');
  const viewBox = source.match(/viewBox="([^"]+)"/)[1];
  const color = source.match(/ color="([^"]+)"/)[1];
  const body = source.replace(/^<svg[^>]+>/, '').replace(/<\/svg>\s*$/, '')
    .replaceAll('id="title"', `id="${id}"`);
  return `<svg x="${x}" y="${y}" width="${size}" height="${size}" viewBox="${viewBox}" color="${color}" aria-hidden="true">${body}</svg>`;
}

function banner(dark) {
  const canvas = dark ? '#111111' : '#F5F5F5';
  const ink = dark ? '#F3F3F3' : '#171717';
  const accent = dark ? '#F3F3F3' : '#171717';
  const logo = dark ? 'logo-dark.svg' : 'logo-light.svg';
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="400" viewBox="0 0 1280 400" role="img" aria-labelledby="banner-title banner-desc">
  <title id="banner-title">Ferry Dock / 渡口 — From your phone. To your computer.</title>
  <desc id="banner-desc">A local text handoff. The two-shore geometric mark connects a phone and a computer without a boat illustration or interface mockup.</desc>
  <rect width="1280" height="400" fill="${canvas}"/>
  <g fill="${ink}" font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif">
    ${mark(logo, 72, 62, 64, 'small-mark-title')}
    <text x="160" y="122" font-size="76" font-weight="500" letter-spacing="-2.5">Ferry Dock</text>
    <text x="590" y="120" font-size="64" font-weight="600" letter-spacing="1">渡口</text>
    <text x="76" y="236" font-size="56" font-weight="500" letter-spacing="-1.2" fill="${accent}">From your phone.</text>
    <text x="76" y="306" font-size="56" font-weight="500" letter-spacing="-1.2">To your computer.</text>
    ${mark(logo, 920, 62, 272, 'large-mark-title')}
  </g>
</svg>
`;
}

const light = banner(false);
const dark = banner(true);
fs.writeFileSync(path.join(root, 'brand', 'banner.svg'), light);
fs.writeFileSync(path.join(root, 'brand', 'banner-dark.svg'), dark);
const renderer = (source, width) => new Resvg(source, {
  fitTo: { mode: 'width', value: width },
  font: { loadSystemFonts: true, defaultFontFamily: 'Heiti SC' },
}).render().asPng();
fs.writeFileSync(path.join(root, 'brand', 'banner.png'), renderer(light, 1280));
// Optional temporary QA outputs. They are not production assets or screenshots.
if (process.argv.includes('--qa')) {
  fs.writeFileSync('/tmp/ferry-dock-banner-320.png', renderer(light, 320));
  fs.writeFileSync('/tmp/ferry-dock-banner-dark.png', renderer(dark, 1280));
  fs.writeFileSync('/tmp/ferry-dock-banner-dark-320.png', renderer(dark, 320));
}
console.log('Wrote brand/banner.svg, brand/banner-dark.svg, and brand/banner.png');
