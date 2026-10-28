# 渡口 / Ferry Dock — brand assets

**手机上的文字，渡到电脑。**

A small local bridge from your phone to your computer.

The mark is a pair of opposing docks with a short crossing between them. The docks turn in opposite directions to give the shape movement and avoid a literal boat or a pair of code brackets. It is a single-colour silhouette: the idea does not depend on an accent colour, animation, or fine detail.

Open [preview.html](preview.html) for light and dark applications, actual 16/24/32 px checks, the colour palette, and spacing examples. It uses only relative local SVGs and system fonts; there are no remote fonts, scripts, or image services.

[PNG brand sheet](preview.png) · [editable SVG sheet](preview.svg). The PNG was
rendered from the vector sources with resvg 2.6.2 and visually inspected. It is a
brand presentation, not a browser or real-device acceptance screenshot.

To regenerate this optional design artifact without adding a production dependency:

```sh
npm install --prefix /tmp/ferry-dock-renderer --ignore-scripts --no-audit --no-fund @resvg/resvg-js@2.6.2
NODE_PATH=/tmp/ferry-dock-renderer/node_modules node scripts/render-brand.cjs
```

The script uses installed system fonts; exported letter shapes can vary by system.
The transfer executable itself remains a Go binary and does not need Node or resvg.

Computed WCAG contrast ratios for the UI palette: primary text on canvas 13.70:1
(light) / 14.92:1 (dark); secondary text 5.89:1 / 8.65:1; primary button text
7.32:1 / 9.50:1. These are colour calculations, not an accessibility certification.

## Assets

| File | Use |
| --- | --- |
| `logo-light.svg` | Standalone mark for light backgrounds, `#142D29`. |
| `logo-dark.svg` | Standalone mark for dark backgrounds, `#F0F6F2`. |
| `logo-mono.svg` | One-colour mark using `currentColor`; defaults to black when loaded as a standalone image. |
| `wordmark-light.svg` | Bilingual lockup for light backgrounds; Chinese primary, English secondary. |
| `wordmark-dark.svg` | Bilingual lockup for dark backgrounds. |
| `wordmark-mono.svg` | Bilingual lockup using `currentColor`. |
| `favicon.svg` | Dedicated 16 px, integer-aligned mark with a light/dark media query. |

All assets are editable native SVG. The three mark variants share one geometry; they are colour variants, not alternate logo concepts. Assets have transparent backgrounds. A fixed-colour external SVG does not inherit CSS `color` from its parent HTML element; inline `logo-mono.svg` when inheritance is needed, or use the supplied light/dark files. When inlining several assets in one document, give each title a unique ID and update its `aria-labelledby`; a decorative mark next to the product name can instead use `aria-hidden="true"`.

## Grid and clear space

- Master mark: `32 × 32` viewBox; visible shape occupies `24 × 24`, from `(4,4)` to `(28,28)`.
- The docks are 4 units thick. The crossing is 8 units wide and 4 units high. All critical edges fall on the 2-unit grid and remain pixel aligned at 16 px.
- Minimum icon size: 16 CSS px. Use 24 or 32 px for ordinary UI; use the wordmark at 160 px wide or larger.
- Minimum clear space beyond the image box: 4 units on a 32-unit mark, or one dock thickness. The built-in 4-unit padding is part of the drawing and does not replace that external clear space.
- Preserve proportions, the central gap, and the opposing dock directions. Do not stretch, rotate, round individual corners, add a boat, or remove the crossing.
- Keep the mark and bilingual text together when using a wordmark file. When space is tight, use the mark by itself rather than squeezing the text.

The favicon is the same silhouette expressed directly on a `16 × 16` grid: 2 px dock thickness, a 4 × 2 px crossing, and at least 2 px between the crossing and either vertical dock. It does not rely on a hairline stroke or antialiasing to preserve its negative space.

## Colour

| Role | Light | Dark |
| --- | --- | --- |
| Canvas | `#F7F8F4` | `#102321` |
| Surface | `#FFFFFF` | `#17312D` |
| Primary text / mark | `#142D29` | `#F0F6F2` |
| Secondary text | `#52645E` | `#ADC1BA` |
| Accent | `#0B6159` | `#76D6C6` |
| Border | `#D6DFD8` | `#35534C` |

Use primary text colour for the normal logo. Reserve the deep teal accent for a primary action, a selection, or a small supporting detail. Keep large surfaces calm. Avoid gradients, glow, shadows inside the logo, and colour treatments that weaken its silhouette. On photography or busy backgrounds, place the mark on a solid approved surface with clear space.

## Typography and naming

The public name is **渡口**; **Ferry Dock** is its English name. Use `ferry-dock` for the repository and executable identifier where appropriate. Do not abbreviate the public name to “FD” in the primary lockup.

Wordmarks retain editable text and use the system stack:

```css
font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
  "PingFang SC", "Microsoft YaHei", sans-serif;
```

Chinese uses weight 600; English uses weight 500. The SVG contains no embedded or redistributed font. Exact letter shapes and line metrics can vary across operating systems; this is an intentional system-font lockup, not a claim of identical outlined lettering. Confirm both scripts on the export system before preparing print material. The geometric mark has no font dependency.

## Accessibility and licensing

Standalone SVGs contain a descriptive title. In HTML, give meaningful brand images `alt="渡口 / Ferry Dock"`; use an empty alt when the same adjacent text already names the product. Do not use the mark alone to convey a session's connection, error, or success state.

The original geometric artwork and these source files are distributed under the repository's [MIT license](../LICENSE). No font software or upstream logo artwork is bundled here. The project name is a product identifier; this document does not claim registered trademark status, exclusivity, or trademark clearance.
