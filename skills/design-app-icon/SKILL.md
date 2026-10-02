---
name: design-app-icon
description: Find, customize, or create app icons from Lucide SVGs and deliver a macOS Retina and Liquid Glass download bundle. Use for icon requests, defaulting to macOS app icons unless the user specifies another source, platform, or an inline UI icon.
---

# App Icon Designer

Turn an app's purpose and the user's visual preferences into usable icon files.
Default to Lucide artwork, the current macOS app-icon design, and native Liquid
Glass. Honor supplied artwork, an existing design, and explicit source, style,
platform, or output-format choices. A request for references only stays research.

## Find and adapt

1. Infer the app's purpose, name, palette, and desired character from the request.
   Ask only when a missing detail materially changes the design. For revisions,
   start with the already selected artwork rather than repeating discovery.
2. Search [Lucide](https://lucide.dev/icons/) for two to four semantically suitable,
   visibly distinct candidates. Inspect each shortlisted SVG and explain the
   recommendation briefly with source links. Judge silhouette, balance, and
   small-size recognition as well as the icon's name. Broaden to another library
   if Lucide does not fit or the user requests alternatives; do not claim a
   cross-library search when only Lucide was inspected.
3. Obtain the SVG and applicable license from the official source. Prefer a
   release or commit-pinned URL when recording provenance. Raw Lucide files live
   at `https://raw.githubusercontent.com/lucide-icons/lucide/{ref}/icons/{name}.svg`;
   the repository's `LICENSE` contains the ISC terms and any inherited notices.
   Keep those notices in the deliverable. An open-source glyph is not an exclusive
   or original brand mark.
4. Follow an explicit selection. Otherwise recommend and proceed with a strong
   candidate when the brief is sufficient; do not introduce an approval gate.
   If the user wants several finished alternatives, package each. Modify geometry,
   stroke weight, palette, spacing, and enclosure to suit this request. For a
   worked example with the original results, read
   [the Relay case](example/EXAMPLE.md). Its teal palette and selected
   symbols are examples, not universal defaults.

## Use current macOS conventions

Before deciding geometry or material settings, read Apple's current
[App icons guidance](https://developer.apple.com/design/human-interface-guidelines/app-icons)
and [Icon Composer guide](https://developer.apple.com/documentation/xcode/creating-your-app-icon-using-icon-composer).
Use the current [design resources](https://developer.apple.com/design/resources/)
when a flattened enclosure template is needed. If those sources are unavailable,
use the documented baseline and identify it instead of claiming a fresh check.

Read [references/macos-delivery.md](references/macos-delivery.md) for the native
document, Retina representations, tool use, and final package contents.

- Keep the main symbol simple, centered, and legible at small sizes. Match the
  brief; avoid treating a glass effect or a particular palette as the design itself.
- Build native foreground layers as vectors with outlined strokes and no baked
  highlights, blurs, shadows, or corner mask. Use Icon Composer's background and
  let the system supply its current enclosure and material rendering.
- Deliver an actual `.icon` package, including `icon.json` and its referenced
  assets. A PNG, renamed file, or loose SVG layers alone are not a native document.
- Configure native glass, restrained translucency, highlights, and supported
  refraction, plus coherent default/dark/mono appearances. Do not guess new
  serialization keys or assume an older example is the latest format.
- Produce static PNG, ICNS, and Xcode asset-catalog fallbacks from vector artwork.
  Render every size independently; do not enlarge a screenshot or small PNG.

## Build and check

Use [scripts/build_icon.py](scripts/build_icon.py) for a simple Lucide-derived
symbol. It resolves `currentColor`, expands strokes, normalizes vector artwork,
and creates a native document and the static macOS resources. It runs locally and
does not contact a generator or upload anything. Choose colors and proportions
for the current request; inspect `--help` for adjustments.

```bash
uv run <skill-dir>/scripts/build_icon.py build \
  --name Relay-Orbit --svg <edited-svg> \
  --license <source-license> --source-url <source-svg-url> \
  --background '#497B77' '#214E51' --foreground '#EEF5EF' \
  --stroke-width 1.65 --output <deliverables-dir>
```

The helper's documented geometry and material defaults are a dated baseline.
Adjust them or the resulting document when the current guidance or the brief
requires it. For a complex layered design or another platform, adapt the assets
and document deliberately instead of forcing it through the one-symbol helper.

Run `verify <bundle-directory>` after modifications. Check referenced assets,
vector bounds, transparency, license/provenance, PNG dimensions and color
profiles, all 10 macOS 1x/2x slots, and ICNS decoding. These checks do not validate
Apple's native rendering or substitute for an Xcode build.

## Native preview is optional

If an already available and authorized **local Mac Computer Use** surface can
operate Icon Composer, use it to open the generated document, inspect default,
dark, and mono appearances at large and small sizes, adjust material settings,
save the document, and export or capture a real preview. Follow the environment's
Computer Use instructions. Inspect the app state before acting and read the
latest state after each meaningful UI change. Exported artwork is preferable to
a screenshot of the whole editor; label editor screenshots as such.

If no usable local Mac or Icon Composer is available, **skip native preview and
continue to delivery**. Do not block on connecting a Mac, installing software,
granting desktop access, or adding a remote Mac solely for this optional step.
Do not report a code-rendered approximation as an Icon Composer preview. Record
what was actually checked, and whether native opening, preview, and compilation
were performed; do not infer one from another.

## Deliver

Package the `.icon`, edited and original SVGs, PNG master, `.icns`,
`AppIcon.appiconset`, source license, provenance, and short integration notes.
Include menu-bar template assets when useful and real previews only when obtained.
After a native edit or preview, update the validation notes and run
`pack <bundle-directory>` so the ZIP contains the final files. For several designs,
one combined ZIP is convenient; retain clearly named per-design directories.

Use the current environment's supported file-delivery mechanism. In Okou web
chat, consult `okou web upload-file --help`, upload the ZIP, and return the exact
download URL. A local path alone is not delivery. Provide individual PNG links
when they serve a separate preview or download need, not as a substitute for the
native package. End with a brief description of the choices, how to use the
files, and the actual native-validation status.
