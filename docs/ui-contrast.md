# Monochrome UI source audit

Reviewed on 2026-10-29 for the alpha.2 UI. This is a calculation and source-layout
review, not a browser test or a claim of complete WCAG conformance.

The reviewed [stylesheet](../internal/relay/web/style.css) has SHA-256
`3d9ce5c3438e7d51aae9523a7743719c6b40d3578d524608e7f4f28143024a8f`.
Recalculate if these colors, opacity, backgrounds, or component rules change.

## Method and criteria

Composite translucent colors over their actual declared parent before computing
relative luminance. For each sRGB channel, `C = alpha * foreground +
(1 - alpha) * background`. Normalize channels to 0–1, linearize with the sRGB
transfer function, then use `L = 0.2126 R + 0.7152 G + 0.0722 B` and
`(lighter L + 0.05) / (darker L + 0.05)`. The calculations retain fractional
channels; values below are rounded only for display.

The reference checks are 4.5:1 for normal text, including placeholders, and 3:1
for necessary control boundaries and focus cues. Disabled controls have an
exception, but their labels are also calculated here. The 3px focus outline is
reviewed as a design rule; focus appearance and clipping still need browser
verification. Sources: [W3C text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
[non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html),
and [focus appearance, Level AAA](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html).

The light panel is `rgba(255,255,255,.92)` over `#f5f5f5`: its effective RGB
channels are **254.2**, rather than an assumed 255. The dark panel is
`rgba(25,25,25,.96)` over `#111`: its channels are **24.68**. There is no additional
parent opacity, color filter, gradient, or shadow beneath these text pairs in
the reviewed stylesheet.

## Calculated pairs

| Element / foreground and background | Light | Dark | Reference |
| --- | ---: | ---: | --- |
| Main text / canvas | 16.444:1 | 17.018:1 | 4.5:1 |
| Main text / composited panel | 17.806:1 | 15.895:1 | 4.5:1 |
| Muted text / canvas | 5.595:1 | 8.128:1 | 4.5:1 |
| Muted text / composited panel | 6.058:1 | 7.592:1 | 4.5:1 |
| Placeholder / textarea surface | 6.100:1 | 7.568:1 | 4.5:1 |
| Primary button label / normal fill | 17.928:1 | 16.157:1 | 4.5:1 |
| Primary button label / hover fill | 12.635:1 | 13.199:1 | 4.5:1 |
| Secondary button label / hover fill | 15.313:1 | 13.463:1 | 4.5:1 |
| Plain button label / hover fill | 5.210:1 | 6.430:1 | 4.5:1 |
| Read-only textarea text / fill | 15.732:1 | 14.684:1 | 4.5:1 |
| Disabled button label / fill | 4.978:1 | 5.681:1 | Informative |
| Input border / outside canvas | 3.084:1 | 3.813:1 | 3:1 |
| Input border / outside panel | 3.340:1 | 3.562:1 | 3:1 |
| Input border / textarea surface | 3.363:1 | 3.550:1 | 3:1 |
| Focus outline / canvas | 16.444:1 | 17.018:1 | 3:1 |
| Focus outline / panel | 17.806:1 | 15.895:1 | 3:1 |

All listed required pairs clear the unrounded reference values. The narrowest
required text margin is the light plain-button hover at 5.210:1. The narrowest
required boundary margin is the light input border against canvas at 3.084:1;
do not lighten that token without recalculating.

`--line` is intentionally decorative: composited over a panel it is 1.290:1
in light mode and 1.525:1 in dark mode. It separates cards, messages, and groups;
it is not used as the sole active textarea boundary or focus cue. Inputs and
secondary buttons use `--input-line`; errors use explicit text, increased weight,
and a 2px `currentColor` status marker.

## Type, states, and layout checks

- Body, input, and request text use 16px; received text uses 15px. Labels and
  statuses use 14px; supporting captions use 13px. The English brand subline is
  11px and the Chinese wordmark is 22px. Small captions use the normal-text
  contrast requirement; this audit does not treat them as large text.
- Placeholders explicitly set `opacity: 1`. Disabled buttons use opaque,
  separately specified foreground/background tokens and `opacity: 1`; hover
  rules exclude disabled controls. Read-only text retains the normal text color
  on its own opaque background.
- Keyboard focus has a 3px outline with 4px offset. Relevant ancestor containers
  do not clip overflow. An 18px mobile outer gutter and internal component
  padding leave room for the 7px outer reach. Actual keyboard navigation,
  focus visibility, text scaling, and forced-colors behavior remain browser checks.
- At a 320px viewport, the mobile shell has 284px of content width. The workspace
  switches to `minmax(0,1fr)`; the inbox has `min-width:0`, and long message,
  request, status, and network text can wrap. Actions and desktop controls wrap.
  The pairing card's border and 14px padding leave approximately **254px** for
  the QR image. No fixed minimum width was found that forces horizontal page
  scrolling in this layout. This is static reasoning, not a rendered 320px or
  [WCAG reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) pass.

## QR presentation

`#qr` has an opaque `#fff` background, no border, no radius, no filter, no
opacity reduction, no overlay, and responsive proportional sizing. The app uses
the pinned `skip2/go-qrcode` default black/white palette; its border is enabled
and `quietZoneSize()` returns four modules. CSS leaves that PNG quiet zone
intact. Black against white is 21:1 in either page theme.

[DENSO WAVE's QR guidance](https://www.qrcode.com/en/howto/code.html) specifies a
clear four-module margin. Source review cannot establish camera decoding success
after scaling, display brightness, or real phone scanning; those remain untested
here. No QR capability or submitted user text was generated or saved for this audit.

## Reproducing the color calculation

This standard-library Python example reproduces the alpha panel and muted-text
rows; use the same function for the other declared foreground/background pairs.

```python
def rgb(value):
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(channel * 2 for channel in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))

def over(foreground, background, alpha):
    return tuple(alpha * f + (1 - alpha) * b
                 for f, b in zip(rgb(foreground), rgb(background)))

def luminance(color):
    channels = rgb(color) if isinstance(color, str) else color
    channels = [channel / 255 for channel in channels]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
              for c in channels]
    return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))

def contrast(foreground, background):
    low, high = sorted((luminance(foreground), luminance(background)))
    return (high + .05) / (low + .05)

for foreground, panel, canvas, alpha in [
    ("#626262", "#fff", "#f5f5f5", .92),
    ("#aaa", "#191919", "#111", .96),
]:
    print(contrast(foreground, over(panel, canvas, alpha)))
# 6.058356019863129
# 7.592309083911943
```

Safari rendering, keyboard/clipboard interaction, real device scanning, and
screenshots are recorded separately by the main task. The alpha.1 startup
measurements apply to alpha.1 only and are not UI or alpha.2 timing evidence.
