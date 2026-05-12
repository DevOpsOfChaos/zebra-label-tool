import fs from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';

function commandExists(command) {
  const probe = process.platform === 'win32' ? 'where' : 'command';
  const args = process.platform === 'win32' ? [command] : ['-v', command];
  const result = spawnSync(probe, args, { stdio: 'ignore', shell: process.platform !== 'win32' });
  return result.status === 0;
}

function line(status, name, detail) {
  console.log(`${status.padEnd(5)} ${name.padEnd(18)} ${detail}`);
}

let hasError = false;
console.log('Zebra Label Tool Tauri prerequisites');
console.log('');

for (const [command, label] of [['node', 'Node.js'], ['npm', 'npm'], ['cargo', 'Cargo']]) {
  if (commandExists(command)) {
    line('OK', label, `${command} found on PATH`);
  } else {
    line('ERROR', label, `${command} not found on PATH`);
    hasError = true;
  }
}

const iconPath = path.join('src-tauri', 'icons', 'icon.ico');
if (fs.existsSync(iconPath)) {
  line('OK', 'Windows icon', iconPath);
} else {
  line('ERROR', 'Windows icon', `${iconPath} missing`);
  hasError = true;
}

const cargoToml = path.join('src-tauri', 'Cargo.toml');
if (fs.existsSync(cargoToml)) {
  line('OK', 'Cargo.toml', cargoToml);
} else {
  line('ERROR', 'Cargo.toml', `${cargoToml} missing`);
  hasError = true;
}

process.exit(hasError ? 1 : 0);
