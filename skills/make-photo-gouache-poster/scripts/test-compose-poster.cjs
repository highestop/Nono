#!/usr/bin/env node
// Verify output geometry, oriented layout, original-photo use, and title confinement.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { test, after } = require('node:test');
const sharp = require('sharp');
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'gouache-compositor-'));
const script = path.join(__dirname, 'compose-poster.cjs');
after(() => fs.rmSync(directory, { recursive: true, force: true }));

async function solid(name, width, height, color, orientation) {
  const file = path.join(directory, name);
  let image = sharp({ create: { width, height, channels: 3, background: color } });
  if (orientation) image = image.withMetadata({ orientation });
  await image.png().toFile(file);
  return file;
}

function run(photo, painting, output, extra = []) {
  const result = spawnSync(process.execPath, [script, '--photo', photo,
    '--painting', painting, '--output', output, ...extra], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

async function pixel(file, left, top) {
  const { data } = await sharp(file).extract({ left, top, width: 1, height: 1 })
    .removeAlpha().raw().toBuffer({ resolveWithObject: true });
  return [...data];
}

test('standalone output keeps each oriented source size and contains only painting', async () => {
  const painting = await solid('standalone-painting.png', 200, 200, '#0000ff');
  for (const [name, width, height, orientation, expected] of [
    ['landscape', 400, 200, undefined, [400, 200]],
    ['portrait', 120, 240, undefined, [120, 240]],
    ['square', 128, 128, undefined, [128, 128]],
    ['rotated', 320, 160, 6, [160, 320]],
  ]) {
    const photo = await solid(`${name}.png`, width, height, '#ff0000', orientation);
    const output = path.join(directory, `${name}-poster.png`);
    const info = run(photo, painting, output, ['--mode', 'poster-only']);
    const actual = await sharp(output).metadata();
    assert.deepEqual([actual.width, actual.height], expected);
    assert.deepEqual(info.size, expected);
    assert.equal(info.photo, null);
    assert.equal(info.splitAt, null);
    assert.deepEqual(await pixel(output, 0, 0), [0, 0, 255]);
    assert.deepEqual(await pixel(output, actual.width - 1, actual.height - 1), [0, 0, 255]);
  }
});

test('auto collage uses oriented shape and fills an exact square half split', async () => {
  const painting = await solid('collage-painting.png', 200, 200, '#0000ff');
  for (const [name, width, height, orientation, expected] of [
    ['wide', 400, 200, undefined, 'top-bottom'],
    ['tall', 120, 240, undefined, 'left-right'],
    ['equal', 128, 128, undefined, 'top-bottom'],
    ['exif', 320, 160, 6, 'left-right'],
  ]) {
    const photo = await solid(`${name}-source.png`, width, height, '#ff0000', orientation);
    const output = path.join(directory, `${name}-collage.png`);
    const info = run(photo, painting, output, ['--size', '256']);
    const metadata = await sharp(output).metadata();
    assert.deepEqual([metadata.width, metadata.height], [256, 256]);
    assert.equal(info.layout, expected);
    assert.equal(info.splitAt, 128);
    const before = expected === 'top-bottom' ? [128, 127] : [127, 128];
    const afterSplit = expected === 'top-bottom' ? [128, 128] : [128, 128];
    assert.deepEqual(await pixel(output, ...before), [255, 0, 0]);
    assert.deepEqual(await pixel(output, ...afterSplit), [0, 0, 255]);
    assert.deepEqual(await pixel(output, 255, 255), [0, 0, 255]);
  }
});

test('explicit layout overrides auto and focus selects the retained photo region', async () => {
  const photo = path.join(directory, 'focus-source.png');
  const green = await solid('green-half.png', 200, 200, '#00ff00');
  await sharp({ create: { width: 400, height: 200, channels: 3, background: '#ff0000' } })
    .composite([{ input: green, left: 200, top: 0 }]).png().toFile(photo);
  const painting = await solid('focus-painting.png', 100, 200, '#0000ff');
  for (const [focus, expected] of [['0', [255, 0, 0]], ['1', [0, 255, 0]]]) {
    const output = path.join(directory, `focus-${focus}.png`);
    const info = run(photo, painting, output,
      ['--size', '200', '--layout', 'left-right', '--photo-focus', focus]);
    assert.equal(info.layout, 'left-right');
    assert.deepEqual(await pixel(output, 50, 100), expected);
  }
});

test('title placement cannot alter the photo half or escape the painted region', async () => {
  const photo = await solid('title-source.png', 120, 240, '#ff0000');
  const painting = await solid('title-painting.png', 120, 240, '#0000ff');
  const title = path.join(directory, 'title.png');
  const ink = await solid('title-ink.png', 16, 80, '#000000');
  await sharp({ create: { width: 20, height: 100, channels: 4,
    background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([{ input: ink, left: 2, top: 10 }]).png().toFile(title);
  const base = path.join(directory, 'title-base.png');
  const output = path.join(directory, 'with-title.png');
  run(photo, painting, base, ['--size', '256']);
  run(photo, painting, output, ['--size', '256', '--title-art', title,
    '--title-width', '128', '--title-top', '250', '--title-x', '0']);
  const photoRegion = { left: 0, top: 0, width: 128, height: 256 };
  assert.deepEqual(await sharp(output).extract(photoRegion).raw().toBuffer(),
    await sharp(base).extract(photoRegion).raw().toBuffer());
  assert.notDeepEqual(await sharp(output).raw().toBuffer(), await sharp(base).raw().toBuffer());
});

test('rejects an odd square, standalone layout/size, and opaque title artwork', async () => {
  const photo = await solid('invalid-source.png', 100, 200, '#ff0000');
  const painting = await solid('invalid-painting.png', 100, 200, '#0000ff');
  const opaque = path.join(directory, 'opaque-title.png');
  await sharp({ create: { width: 20, height: 20, channels: 4,
    background: { r: 0, g: 0, b: 0, alpha: 1 } } }).png().toFile(opaque);
  for (const extra of [
    ['--size', '255'], ['--mode', 'poster-only', '--size', '256'],
    ['--mode', 'poster-only', '--layout', 'auto'], ['--title-art', opaque],
  ]) {
    const result = spawnSync(process.execPath, [script, '--photo', photo,
      '--painting', painting, '--output', path.join(directory, 'invalid.png'), ...extra],
    { encoding: 'utf8' });
    assert.notEqual(result.status, 0, extra.join(' '));
  }
});
