# Imagegen prompts

Replace angle-bracket placeholders with observations, measured dimensions, and exact chosen text. Image 1 is the user's scene; Image 2 is the supplied gouache sample for paint treatment only. If the lettering sample is included, label it as lettering style only. Never copy sample landmarks or words into the user's image.

## Standalone poster

```text
Use case: style-transfer. Asset: a finished standalone gouache poster with title.
Canvas: <oriented-source-width> × <oriented-source-height>, ratio <width:height>. Preserve this source ratio; do not substitute a generic portrait or square shape.
Image 1 supplies the scene, recognizable subjects, perspective and spatial relationships. Image 2 supplies only soft gouache treatment, matte pigment, warm paper grain and quiet art-book atmosphere.

Paint <observed subject and scene>. Retain <distinctive features and their spatial relationships>. Simplify photographic detail into translucent soft gouache, washes, dry brush, broken pigment and softly dissolving edges. Use restrained blue-grey, warm ivory and taupe alongside the photo's recognizable local colors and supported warm accents. Keep food colors appetizing when present. Avoid harsh outlines, vector geometry, 3D and excessive HDR.

The exact sole title is "<TITLE>". Place it in <calm light area within the scene>, clear of <main subject / skyline>. Use airy hand-painted lettering, smoky blue-grey, slightly irregular brush strokes and dry-brush ends, no serifs, outlines or shadows. For Latin text, use <exact chosen capitalization>. Fit long text with smaller lettering or two balanced lines, preserving spelling and punctuation.

One continuous painted scene fills the canvas edge to edge. No photo panel, collage, separate title band, border, blank padding, duplicate scene, invented landmarks or additional captions. Paper texture is integrated into the painting.
```

For an untitled working painting, replace the title paragraph with: `No title or legible text. Leave calm, light painted space at <position> for a title added after final fitting.`

## Collage panel

```text
Use case: style-transfer. Asset: ONLY the painted half of a square photo-and-gouache collage. No title or legible text.
Panel shape: <2:1 landscape for top-bottom / 1:2 portrait for left-right>. This is a painted panel, not the finished two-panel collage.
Image 1 supplies the user's scene and composition. Image 2 supplies paint treatment only; do not copy its landmarks.

Paint <observed subject and scene>, preserving <main subject, distinctive features and spatial relationships>. Adapt framing to the required panel while keeping the main subject recognizable. Use soft translucent gouache, matte washes, dry brush, broken pigment and warm-ivory paper grain. Retain source-supported colors in a restrained palette, with atmospheric blue-grey and taupe where suitable. No photographic pixels, cartoon outlines, vector look, 3D or excessive HDR.

Reserve a calm, light painted area near <title position>, away from <main subject / skyline>. Fill the entire panel with painting and integrated paper texture; no margins, borders, photo panel, collage, letters, invented landmarks or extra subjects.
```

Check the actual aspect ratio and intended crop before composing. Regenerate if fitting the panel would remove the subject or title area.

## Lettering

```text
Asset: isolated title artwork on a genuinely transparent background. The lettering sample supplies only brush style, not its words.
Only content: "<TITLE>". Spell every character and punctuation mark exactly; no extra words.
Use airy hand-painted lettering in translucent smoky blue-grey gouache (#65747B), fine-to-medium slightly uneven strokes, dry-brush ends and subtle pigment granulation. No serifs, outlines, shadows, heavy block weight or decorative flourishes. Preserve the exact chosen capitalization and script. Use one centered line when it fits, or <explicit two-line break> for a long title.
No background or extra imagery; retain genuine alpha transparency.
```

Check spelling, full alpha, and edges before composition. The compositor removes colored fringes by greyscale/tint processing while preserving alpha. If generation repeatedly misspells a title, use an accurately typeset fallback with an appropriate script/font and subtle painted treatment; disclose any visible style compromise.

## Title-only edit

Prefer retained untitled artwork and a new transparent wordmark when available. Otherwise edit the finished poster through built-in `imagegen`:

```text
Use case: text-localization. Edit target: the supplied finished poster.
Replace ONLY the existing heading "<OLD TITLE>" with exact text "<NEW TITLE>" in <existing title area>. Match the current smoky blue-grey hand-painted brush lettering, without serif terminals. Reduce size or use <line break> to fit without covering the subject. Remove all traces of the old heading.
Preserve canvas <width> × <height>, ratio, crop, composition, subjects, buildings, colors, lighting and paper treatment. Do not recompose the scene or add captions. In a collage, the title must remain entirely within the painted half; preserve the actual photo separately with deterministic composition rather than regenerating it.
```
