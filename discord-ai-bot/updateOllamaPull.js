#!/usr/bin/env node
// updateOllamaPull.js
// Syncs the model in ollamaModel.ts to the ollama:pull script in package.json

const fs = require('fs');
const path = require('path');

const modelFile = path.join(__dirname, 'src', 'ai', 'ollamaModel.ts');
const pkgFile = path.join(__dirname, 'package.json');

// Read model from ollamaModel.ts
const modelSrc = fs.readFileSync(modelFile, 'utf-8');
const match = modelSrc.match(/export const OLLAMA_MODEL = "([^"]+)"/);
if (!match) {
  console.error('Could not find OLLAMA_MODEL in ollamaModel.ts');
  process.exit(1);
}
const model = match[1];

// Read and update package.json
const pkg = JSON.parse(fs.readFileSync(pkgFile, 'utf-8'));
if (!pkg.scripts || !pkg.scripts['ollama:pull']) {
  console.error('No ollama:pull script found in package.json');
  process.exit(1);
}
pkg.scripts['ollama:pull'] = `ollama pull ${model}`;
fs.writeFileSync(pkgFile, JSON.stringify(pkg, null, 2));
console.log(`Updated ollama:pull script to use model: ${model}`);
