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

Computed WCAG contrast ratios for the neutral UI palette: primary text on canvas
16.44:1 (light) / 17.02:1 (dark); secondary text 5.59:1 / 8.13:1;
primary button text 17.93:1 / 16.16:1. These are colour calculations,
not an accessibility certification. QR images keep an opaque white background
and their original quiet zone in both themes; no alpha, filters, or rounded
cropping are applied to the code.

## Assets

| File | Use |
| --- | --- |
| `logo-light.svg` | Standalone mark for light backgrounds, `#171717`. |
| `logo-dark.svg` | Standalone mark for dark backgrounds, `#F3F3F3`. |
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
| Canvas | `#F5F5F5` | `#111111` |
| Surface | `#FFFFFF` | `#191919` |
| Primary text / mark | `#171717` | `#F3F3F3` |
| Secondary text | `#626262` | `#AAAAAA` |
| Primary action | `#171717` | `#F3F3F3` |
| Border | `rgba(17,17,17,.12)` | `rgba(255,255,255,.14)` |

Border swatches in the previews show the alpha colour composited over its
corresponding canvas (`#DADADA` light / `#323232` dark). Keep the alpha token
in the UI; these soft separators do not replace the stronger input boundary
or keyboard focus outline.

Use primary text colour for the normal logo. Use a black-on-light or white-on-dark primary action. Keep the canvas and panels neutral, with subtle alpha borders separating groups. Do not reduce the opacity of a whole control to indicate that it is disabled; use independent label and surface colours. Avoid gradients, glow, shadows inside the logo, and colour treatments that weaken its silhouette. On photography or busy backgrounds, place the mark on a solid approved surface with clear space.

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


## README banner

The README banner uses the existing mark, product name, and one ordinary-transfer
value statement: **From your phone. To your computer.** / **从手机，到电脑。**
It does not claim Agent automation, encrypted transport, file support, or an
unreleased installation method.

- [banner.svg](banner.svg): editable, self-contained light artwork.
- [banner-dark.svg](banner-dark.svg): the same composition for dark backgrounds.
- [banner.png](banner.png): rendered light preview for image viewers and sharing.

The artboard is 1280 × 400. English and Chinese names stay visible at a 320 px
image width, and the two value lines are 14 px after that scale. The artwork uses
system fonts, not downloaded or embedded font software. Exact font metrics may
vary; the PNG records one export with the installed system-font fallback. The
PNG and both 320 px light/dark checks have been visually inspected. These are
brand graphics, not application screenshots.

For a README, use the theme-aware SVGs and meaningful alternative text:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="brand/banner-dark.svg">
  <img src="brand/banner.svg" alt="Ferry Dock / 渡口 — From your phone. To your computer.">
</picture>
```

Regenerate from the canonical geometric marks with the same optional renderer
used for the brand sheet:

```sh
NODE_PATH=/tmp/ferry-dock-renderer/node_modules node scripts/render-banner.cjs
```

Pass `--qa` to also render 320 px light/dark checks and the full dark preview
under `/tmp`; those temporary QA images are not distributed product assets.
