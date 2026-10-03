# Imagegen prompts

Replace the bracketed scene details with observations from the current photo. Keep the roles of the two references explicit. These prompts generated the approved visual direction; adapt them to the picture rather than reusing Hong Kong content.

## Painting

```text
Use case: style-transfer. Asset type: only the painted panel of a square editorial poster: wide 2:1 for a top/bottom layout or tall 1:2 for a left/right layout. No title or text. Image 1 is the user's photo and supplies the scene, recognizable subjects, and spatial relationships. Image 2 is the supplied gouache sample and supplies only paint treatment, palette, paper texture, and quiet art-book mood; do not copy its Hong Kong landmarks.

Paint an interpretive but recognizable view of [observed scene, main subject, and distinctive features]. Retain the approximate relationships among [important forms and background elements]. Simplify photographic detail into translucent soft gouache, dry brush, watercolor-like opacity, matte pigment, broken strokes, and subtle warm-ivory paper grain. Let edges dissolve gently into the atmosphere. Use mist blue-grey, smoke grey, warm ivory, muted taupe, and only a few soft warm-yellow accents where the photo supports them. Keep the composition balanced and quiet with light open space near the top for a separately added title. Sophisticated Japanese editorial / Scandinavian art-book feel.

No words, letters, logos, border, cartoon outlines, vector icons, 3D, cyberpunk colors, excessive HDR, or invented landmarks. Do not reproduce the source photo pixel for pixel.
```

If imagegen produces a 3:2 or 2:3 panel, crop only after checking that the final 2:1 or 1:2 view retains the scene and title space.

## Lettering

```text
Asset type: isolated title artwork for the gouache poster. Genuine transparent background. Image 1 is the approved hand-painted lettering sample and supplies brush style only, not its words.

The only content is the exact user title: "<TITLE>". Spell it exactly, with no extra text. Render it as airy uppercase lettering hand-painted with a small watercolor brush: fine to medium slightly uneven strokes, subtle dry-brush ends, tiny pigment granulation, translucent smoky blue-grey gouache (#65747B). Simple open letterforms without serifs or geometric digital precision; quietly elegant like a Japanese art-book title. Keep the words on one centered horizontal line when they fit, with generous spacing and clear legibility.

No background, black outline, shadow, bold block weight, decorative flourishes, logo, or extra imagery.
```

Inspect at full size. If transparent edges have cyan or colored artifacts, the compositor desaturates and tints the title while retaining its alpha and pigment variation. For a long title, reduce width or use two balanced lines rather than misspelling or clipping it.
