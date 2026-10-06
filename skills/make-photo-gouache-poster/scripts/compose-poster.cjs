#!/usr/bin/env node
// Finish a source-ratio painting or a square photo/painting collage with sharp.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
const args = process.argv.slice(2);

if (args.includes('--help') || args.length === 0) {
  console.log(`Usage: node compose-poster.cjs --photo <file> --painting <file> --output <png>
  [--mode poster-only|collage] [--layout auto|top-bottom|left-right]
  [--size <even-square-side>] [--title-art <transparent-png>]
  [--photo-focus 0..1] [--painting-focus 0..1] [--grade-photo]
  [--title-width <pixels>] [--title-top <pixels>]
  [--title-x 0..1] [--title-color <hex>]

Defaults: mode=collage, layout=auto, size=2048, focus=0.5.
poster-only uses the photo's EXIF-oriented dimensions as its output size;
the photo is a geometry reference only and is not placed in that output.
collage chooses top/bottom for landscape or square photos, left/right for portraits.
Photo is first; painting is second. Each fills exactly half with no padding.
Focus 0 crops from top/left; 1 crops from bottom/right. No stretching.
Titles are confined to the painted region. --title-top is relative to that region.
Omit --title-art for an already titled painting. --grade-photo applies subtle grading.
--size and --layout are collage-only; poster-only always preserves source geometry.`);
  process.exit(0);
}

function option(name, fallback) {
  const index = args.indexOf(`--${name}`);
  if (index === -1) return fallback;
  const value = args[index + 1];
  if (!value || value.startsWith('--')) throw new Error(`Missing value for --${name}`);
  return value;
}

function required(name) {
  const value = option(name);
  if (!value) throw new Error(`Missing --${name}`);
  return value;
}

function numberOption(name, fallback, min, max) {
  const value = Number(option(name, String(fallback)));
  if (!Number.isFinite(value) || value < min || value > max) {
    throw new Error(`--${name} must be between ${min} and ${max}`);
  }
  return value;
}

async function orientedImage(file) {
  const buffer = await sharp(file).rotate().png().toBuffer();
  const { width, height } = await sharp(buffer).metadata();
  return { buffer, width, height };
}

async function panel(source, width, height, focus, grade = false) {
  const ratio = width / height;
  let crop;
  if (source.width / source.height < ratio) {
    const cropHeight = Math.max(1, Math.min(source.height, Math.round(source.width / ratio)));
    crop = { left: 0, top: Math.round((source.height - cropHeight) * focus),
      width: source.width, height: cropHeight };
  } else {
    const cropWidth = Math.max(1, Math.min(source.width, Math.round(source.height * ratio)));
    crop = { left: Math.round((source.width - cropWidth) * focus), top: 0,
      width: cropWidth, height: source.height };
  }
  let pipeline = sharp(source.buffer).extract(crop).resize(width, height, { kernel: 'lanczos3' });
  if (grade) pipeline = pipeline.modulate({ saturation: 0.93, brightness: 1.01 });
  return { buffer: await pipeline.png().toBuffer(), crop,
    sourceSize: [source.width, source.height] };
}

async function titleLayer(file, region) {
  const metadata = await sharp(file).metadata();
  if (!metadata.hasAlpha) throw new Error('Title artwork must have genuine transparency');
  const stats = await sharp(file).stats();
  const alpha = stats.channels[stats.channels.length - 1];
  if (alpha.min === 255 || alpha.max === 0) {
    throw new Error('Title artwork needs both visible content and transparent pixels');
  }
  const width = Math.round(numberOption('title-width', region.width * 0.5, 1, region.width));
  const top = Math.round(numberOption('title-top', region.height * 0.06, 0, region.height - 1));
  const center = numberOption('title-x', 0.5, 0, 1);
  const color = option('title-color', '#62717a');
  // Fit long/multiline lettering inside the painted region, including its height.
  const title = await sharp(file).trim().greyscale().tint(color)
    .resize({ width, height: Math.max(1, region.height - top), fit: 'inside' })
    .png().toBuffer({ resolveWithObject: true });
  const left = Math.max(0, Math.min(region.width - title.info.width,
    Math.round(region.width * center - title.info.width / 2)));
  return { input: title.data, left: region.left + left, top: region.top + top };
}

async function main() {
  const photoPath = required('photo');
  const paintingPath = required('painting');
  const outputPath = required('output');
  const mode = option('mode', 'collage');
  if (!['poster-only', 'collage'].includes(mode)) {
    throw new Error('--mode must be poster-only or collage');
  }
  if (mode === 'poster-only' && (args.includes('--size') || args.includes('--layout'))) {
    throw new Error('--size and --layout are collage-only; poster-only preserves source geometry');
  }
  if (option('photo-fit', 'cover') !== 'cover') {
    throw new Error('Panels must fill their regions; adjust focus instead of adding padding');
  }
  const photoFocus = numberOption('photo-focus', 0.5, 0, 1);
  const paintingFocus = numberOption('painting-focus', 0.5, 0, 1);
  const source = await orientedImage(photoPath);
  const paintedSource = await orientedImage(paintingPath);
  let width = source.width;
  let height = source.height;
  let layout = null;
  let half = null;
  let region = { width, height, left: 0, top: 0 };
  const layers = [];
  let photo = null;

  if (mode === 'collage') {
    const side = numberOption('size', 2048, 2, 32768);
    if (!Number.isInteger(side) || side % 2 !== 0) {
      throw new Error('--size must be an even integer for an exact half split');
    }
    layout = option('layout', 'auto');
    if (layout === 'auto') layout = source.width >= source.height ? 'top-bottom' : 'left-right';
    if (!['top-bottom', 'left-right'].includes(layout)) {
      throw new Error('--layout must be auto, top-bottom or left-right');
    }
    width = height = side;
    half = side / 2;
    region = layout === 'left-right'
      ? { width: half, height: side, left: half, top: 0 }
      : { width: side, height: half, left: 0, top: half };
    photo = await panel(source, region.width, region.height, photoFocus, args.includes('--grade-photo'));
    layers.push({ input: photo.buffer, left: 0, top: 0 });
  }

  const painting = await panel(paintedSource, region.width, region.height, paintingFocus);
  layers.push({ input: painting.buffer, left: region.left, top: region.top });
  const titlePath = option('title-art');
  if (titlePath) layers.push(await titleLayer(titlePath, region));

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  await sharp({ create: { width, height, channels: 3, background: '#f8f5ee' } })
    .composite(layers).png({ compressionLevel: 9 }).toFile(outputPath);
  console.log(JSON.stringify({ outputPath, mode, size: [width, height],
    sourceSize: [source.width, source.height], layout, splitAt: half, paintingRegion: region,
    photo: photo && { sourceSize: photo.sourceSize, crop: photo.crop },
    painting: { sourceSize: painting.sourceSize, crop: painting.crop }, title: Boolean(titlePath) }));
}

main().catch((error) => { console.error(error.message); process.exitCode = 1; });
