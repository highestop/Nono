#!/usr/bin/env node
// Compose the approved 2048 px square layout from a real photo, a painted panel,
// and an optional transparent title artwork. Requires Node.js and sharp.

const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) {
  console.log(`Usage: node compose-poster.cjs --photo <file> --painting <file> --output <png>
  [--layout top-bottom|left-right] [--title-art <transparent-png>]
  [--photo-focus 0..1] [--painting-focus 0..1]
  [--title-width <pixels>] [--title-top <pixels>]
  [--title-x 0..1] [--title-color <hex>]

Focus 0 crops from the top or left; 1 crops from the bottom or right.
Both panels fill their regions using proportional crops; no padding is added.
Defaults: layout=top-bottom, photo-focus=0.5,
painting-focus=1, title-color=#62717a. Title placement adjusts by layout.`);
  process.exit(0);
}

function option(name, fallback) {
  const index = args.indexOf(`--${name}`);
  return index === -1 ? fallback : args[index + 1];
}

function required(name) {
  const value = option(name);
  if (!value || value.startsWith('--')) throw new Error(`Missing --${name}`);
  return value;
}

function numberOption(name, fallback, min, max) {
  const value = Number(option(name, String(fallback)));
  if (!Number.isFinite(value) || value < min || value > max) {
    throw new Error(`--${name} must be between ${min} and ${max}`);
  }
  return value;
}

const side = 2048;
const half = side / 2;
const paper = '#f8f5ee';

async function orientedBuffer(file) {
  return sharp(file).rotate().toBuffer();
}

async function panel(file, targetWidth, targetHeight, focus, grade) {
  const source = await orientedBuffer(file);
  const { width, height } = await sharp(source).metadata();
  let image = sharp(source);
  let crop;
  const targetRatio = targetWidth / targetHeight;
  if (width / height < targetRatio) {
    const cropHeight = Math.round(width / targetRatio);
    const top = Math.round((height - cropHeight) * focus);
    crop = { left: 0, top, width, height: cropHeight };
  } else {
    const cropWidth = Math.round(height * targetRatio);
    const left = Math.round((width - cropWidth) * focus);
    crop = { left, top: 0, width: cropWidth, height };
  }
  image = image.extract(crop).resize(targetWidth, targetHeight, { kernel: 'lanczos3' });

  if (grade) image = image.modulate({ saturation: 0.93, brightness: 1.01 });
  return { buffer: await image.png().toBuffer(), crop, sourceSize: [width, height] };
}

async function main() {
  const photoPath = required('photo');
  const paintingPath = required('painting');
  const outputPath = required('output');
  const titlePath = option('title-art');
  const layout = option('layout', 'top-bottom');
  if (!['top-bottom', 'left-right'].includes(layout)) {
    throw new Error('--layout must be top-bottom or left-right');
  }
  const panelWidth = layout === 'left-right' ? half : side;
  const panelHeight = layout === 'left-right' ? side : half;
  const paintingLeft = layout === 'left-right' ? half : 0;
  const paintingTop = layout === 'left-right' ? 0 : half;
  if (option('photo-fit', 'cover') !== 'cover') {
    throw new Error('Both panels must fill their regions. Adjust --photo-focus instead of adding padding.');
  }
  const photoFocus = numberOption('photo-focus', 0.5, 0, 1);
  const paintingFocus = numberOption('painting-focus', 1, 0, 1);
  const titleWidth = Math.round(numberOption('title-width', layout === 'left-right' ? 480 : 580, 100, 1500));
  const titleTop = Math.round(numberOption('title-top', layout === 'left-right' ? 85 : 70, 0, 1000));
  const titleX = numberOption('title-x', layout === 'left-right' ? 0.37 : 0.5, 0, 1);
  const titleColor = option('title-color', '#62717a');

  const photo = await panel(photoPath, panelWidth, panelHeight, photoFocus, true);
  const painting = await panel(paintingPath, panelWidth, panelHeight, paintingFocus, false);
  const layers = [
    { input: photo.buffer, left: 0, top: 0 },
    { input: painting.buffer, left: paintingLeft, top: paintingTop },
  ];

  if (titlePath) {
    const metadata = await sharp(titlePath).metadata();
    if (!metadata.hasAlpha) throw new Error('Title artwork must have transparency');
    const title = await sharp(titlePath)
      .trim()
      .greyscale()
      .tint(titleColor)
      .resize({ width: titleWidth })
      .png()
      .toBuffer({ resolveWithObject: true });
    layers.push({
      input: title.data,
      left: paintingLeft + Math.floor(panelWidth * titleX - title.info.width / 2),
      top: paintingTop + titleTop,
    });
  }

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  await sharp({ create: { width: side, height: side, channels: 3,
    background: paper } })
    .composite(layers)
    .png({ compressionLevel: 9 })
    .toFile(outputPath);

  console.log(JSON.stringify({ outputPath, size: [side, side], layout,
    splitAt: half, photo: { sourceSize: photo.sourceSize, crop: photo.crop },
    painting: { sourceSize: painting.sourceSize, crop: painting.crop },
    title: Boolean(titlePath) }));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
