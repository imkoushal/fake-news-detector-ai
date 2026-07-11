// Produce a Chrome Web Store-ready build in ./dist.
//
// The source folder keeps the localhost host-permission so `Load unpacked`
// works against a local `uvicorn api:app`. The published build must not ship
// that permission (reviewers flag unused/broad host access), so this script
// copies the runtime files into ./dist and strips the localhost origin from
// manifest.host_permissions.
//
// Usage:  node build.mjs   →   zip the resulting ./dist for upload.
//
// No dependencies — pure Node.

import { cpSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));
const dist = join(root, 'dist');

// Runtime files that ship in the packaged extension.
const RUNTIME = [
  'manifest.json',
  'config.js',
  'background.js',
  'content.js',
  'popup.html',
  'popup.css',
  'popup.js',
  'icon.svg', // used inline by popup.html (SVG is valid inside extension pages)
  'icons',
];

const LOCALHOST = 'http://localhost:8000/*';

rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });

for (const name of RUNTIME) {
  cpSync(join(root, name), join(dist, name), { recursive: true });
}

// Strip the localhost host-permission from the packaged manifest.
const manifestPath = join(dist, 'manifest.json');
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
const before = manifest.host_permissions.length;
manifest.host_permissions = manifest.host_permissions.filter((p) => p !== LOCALHOST);
if (manifest.host_permissions.length === before) {
  console.warn(`warning: localhost permission (${LOCALHOST}) not found in manifest — nothing stripped`);
}
writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');

console.log(`built dist/ with ${manifest.host_permissions.length} host_permission(s):`);
for (const p of manifest.host_permissions) console.log(`  - ${p}`);
console.log('\nNext: zip the dist/ folder and upload it in the Chrome Web Store dashboard.');
