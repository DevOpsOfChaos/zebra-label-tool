import bwipjs from 'bwip-js';
import './styles.css';
import { listPrinters, printZpl } from './bridge';
import {
  barcodeLabels,
  barcodeOrder,
  modeOrder,
  positionOrder,
  type AppState,
  type BarcodeMode,
  type BarcodeType,
  type CodePosition,
  type Language,
  type Theme,
  type WorkflowMode,
} from './domain';
import { modeLabel, t } from './i18n';
import { buildSpec, calculateLayout, cleanLines, generateOutputZpl, generateZpl, sequenceValues } from './zpl';

const storageKey = 'zebra-label-tool.tauri.state';

const defaultState: AppState = {
  language: (navigator.language || '').toLowerCase().startsWith('de') ? 'de' : 'en',
  theme: 'light',
  mode: 'text_code',
  printer: '',
  printers: [],
  widthMm: 57,
  heightMm: 19,
  dpi: 300,
  copies: 1,
  border: false,
  inverted: false,
  text: 'Device\nESP32-Kitchen',
  caption: 'Device link',
  fontSize: 54,
  alignment: 'center',
  autoFit: true,
  lineGap: 10,
  codeEnabled: true,
  codeType: 'qrcode',
  codeContent: 'https://example.local/device/esp32-kitchen',
  codePosition: 'right',
  codeArea: 120,
  codeMagnification: 5,
  showBarcodeText: true,
  sequence: {
    start: 1,
    count: 10,
    step: 1,
    padding: 3,
    prefix: 'AS-',
    suffix: '',
    template: 'Asset {value}\nRack A',
    barcodeMode: 'value',
  },
  batchText: 'Shelf A\nBox 01\n\nShelf A\nBox 02',
};

let state: AppState = loadState();

function loadState(): AppState {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return { ...defaultState };
    return { ...defaultState, ...JSON.parse(raw), sequence: { ...defaultState.sequence, ...(JSON.parse(raw).sequence ?? {}) } };
  } catch {
    return { ...defaultState };
  }
}

function saveState(): void {
  localStorage.setItem(storageKey, JSON.stringify({ ...state, printers: [] }));
}

function setState(patch: Partial<AppState>): void {
  state = { ...state, ...patch };
  saveState();
  render();
}

function setSequence<K extends keyof AppState['sequence']>(key: K, value: AppState['sequence'][K]): void {
  state = { ...state, sequence: { ...state.sequence, [key]: value } };
  saveState();
  render();
}

function numberValue(id: string, fallback: number): number {
  const el = document.getElementById(id) as HTMLInputElement | null;
  const parsed = Number(el?.value ?? fallback);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function stringValue(id: string, fallback = ''): string {
  const el = document.getElementById(id) as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null;
  return el?.value ?? fallback;
}

function boolValue(id: string): boolean {
  const el = document.getElementById(id) as HTMLInputElement | null;
  return Boolean(el?.checked);
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function modeDescription(mode: WorkflowMode): string {
  const de: Record<WorkflowMode, string> = {
    text: 'Schnelle Textetiketten ohne Code-Ballast.',
    text_code: 'Normaler Alltagsmodus für Text plus Barcode oder QR-Code.',
    code: 'Ein Code steht im Mittelpunkt, optional mit kurzer Beschriftung.',
    sequence: 'Fortlaufende Nummern, Asset-Tags oder Kabelmarkierungen.',
    sequence_code: 'Fortlaufende Nummern mit Barcode oder QR-Code pro Etikett.',
    batch: 'Mehrere unterschiedliche Etiketten aus Textblöcken erzeugen.',
  };
  const en: Record<WorkflowMode, string> = {
    text: 'Fast text labels without code-related controls.',
    text_code: 'Default daily workflow for text plus barcode or QR code.',
    code: 'A code is the primary content, optionally with a short caption.',
    sequence: 'Numbered asset tags, cable markers and serial labels.',
    sequence_code: 'Numbered labels with a barcode or QR code per label.',
    batch: 'Generate multiple different labels from text blocks.',
  };
  return state.language === 'de' ? de[mode] : en[mode];
}

function render(): void {
  document.body.classList.toggle('dark', state.theme === 'dark');
  const app = document.getElementById('app');
  if (!app) return;
  app.innerHTML = `
    <main class="app-shell">
      <aside class="sidebar">
        <div class="brand">
          <h1>${t(state.language, 'appTitle')}</h1>
          <p>${t(state.language, 'appSubtitle')}</p>
        </div>
        <div class="mode-list" aria-label="${t(state.language, 'mode')}">
          ${modeOrder.map(modeButton).join('')}
        </div>
        <div class="settings-stack">
          ${renderPrinterSettings()}
          ${renderLabelSettings()}
          ${renderAppSettings()}
        </div>
      </aside>
      <section class="workspace">
        <div class="toolbar">
          <div class="toolbar-title">
            <h2>${modeLabel(state.language, state.mode)}</h2>
            <p>${modeDescription(state.mode)}</p>
          </div>
          <div class="toolbar-actions">
            <button class="button" id="copyZplBtn">${t(state.language, 'copyZpl')}</button>
            <button class="button" id="exportZplBtn">${t(state.language, 'exportZpl')}</button>
            <button class="button primary" id="printBtn">${t(state.language, 'print')}</button>
          </div>
        </div>
        ${renderTextPanel()}
        ${renderCodePanel()}
        ${renderSequencePanel()}
        ${renderBatchPanel()}
      </section>
      <aside class="preview-pane">
        <div class="preview-header">
          <div>
            <h2>${t(state.language, 'preview')}</h2>
            <p>${summaryText()}</p>
          </div>
          <button class="button ghost" id="refreshPreviewBtn">↻</button>
        </div>
        <div class="preview-stage">
          ${renderPreviewLabel()}
        </div>
        <div class="status" id="statusBox">${t(state.language, 'ready')}</div>
        <textarea class="zpl-box" id="zplBox" spellcheck="false">${escapeHtml(currentZpl())}</textarea>
      </aside>
    </main>
  `;
  bindEvents();
  renderBarcodeCanvas();
}

function modeButton(mode: WorkflowMode): string {
  return `
    <button class="mode-button ${state.mode === mode ? 'active' : ''}" data-mode="${mode}">
      <strong>${modeLabel(state.language, mode)}</strong>
      <small>${modeDescription(mode)}</small>
    </button>
  `;
}

function renderPrinterSettings(): string {
  const printerOptions = [`<option value="">${t(state.language, 'noPrinter')}</option>`]
    .concat(state.printers.map((printer) => `<option value="${escapeAttr(printer)}" ${state.printer === printer ? 'selected' : ''}>${escapeHtml(printer)}</option>`))
    .join('');
  return `
    <details class="card">
      <summary>${t(state.language, 'printerSettings')}</summary>
      <div class="field" style="margin-top:12px">
        <label>${t(state.language, 'printerSettings')}</label>
        <select id="printerSelect">${printerOptions}</select>
      </div>
      <div class="pill-row" style="margin-top:10px">
        <button class="button" id="refreshPrintersBtn">${t(state.language, 'refreshPrinters')}</button>
      </div>
      <p class="help">${t(state.language, 'printerBridge')}</p>
    </details>
  `;
}

function renderLabelSettings(): string {
  return `
    <details class="card" open>
      <summary>${t(state.language, 'labelSettings')}</summary>
      <div class="grid-2" style="margin-top:12px">
        ${numberField('widthMm', t(state.language, 'width'), state.widthMm, 20, 160)}
        ${numberField('heightMm', t(state.language, 'height'), state.heightMm, 10, 120)}
        <div class="field"><label>${t(state.language, 'dpi')}</label><select id="dpi"><option ${selected(state.dpi, 203)}>203</option><option ${selected(state.dpi, 300)}>300</option><option ${selected(state.dpi, 600)}>600</option></select></div>
        ${numberField('copies', t(state.language, 'copies'), state.copies, 1, 999)}
      </div>
      <div class="checkbox-row" style="margin-top:12px">
        <label><input id="border" type="checkbox" ${state.border ? 'checked' : ''}> ${t(state.language, 'border')}</label>
        <label><input id="inverted" type="checkbox" ${state.inverted ? 'checked' : ''}> ${t(state.language, 'inverted')}</label>
      </div>
    </details>
  `;
}

function renderAppSettings(): string {
  return `
    <details class="card">
      <summary>${t(state.language, 'appTitle')}</summary>
      <div class="grid-2" style="margin-top:12px">
        <div class="field"><label>${t(state.language, 'language')}</label><select id="language"><option value="de" ${state.language === 'de' ? 'selected' : ''}>Deutsch</option><option value="en" ${state.language === 'en' ? 'selected' : ''}>English</option></select></div>
        <div class="field"><label>${t(state.language, 'theme')}</label><select id="theme"><option value="light" ${state.theme === 'light' ? 'selected' : ''}>Light</option><option value="dark" ${state.theme === 'dark' ? 'selected' : ''}>Dark</option></select></div>
      </div>
    </details>
  `;
}

function renderTextPanel(): string {
  const visible = state.mode === 'text' || state.mode === 'text_code' || state.mode === 'code' || state.mode === 'sequence' || state.mode === 'sequence_code';
  if (!visible) return '';
  const isCodeOnly = state.mode === 'code';
  return `
    <section class="card-panel">
      <div>
        <h3>${isCodeOnly ? t(state.language, 'caption') : t(state.language, 'labelText')}</h3>
        <p class="help">${t(state.language, 'labelTextHelp')}</p>
      </div>
      <textarea id="textInput" spellcheck="false">${escapeHtml(isCodeOnly ? state.caption : state.text)}</textarea>
      <div class="grid-3">
        ${numberField('fontSize', 'Font', state.fontSize, 8, 160)}
        ${numberField('lineGap', 'Line gap', state.lineGap, 0, 80)}
        <div class="field"><label>Alignment</label><select id="alignment"><option value="left" ${state.alignment === 'left' ? 'selected' : ''}>${t(state.language, 'left')}</option><option value="center" ${state.alignment === 'center' ? 'selected' : ''}>${t(state.language, 'center')}</option><option value="right" ${state.alignment === 'right' ? 'selected' : ''}>${t(state.language, 'right')}</option></select></div>
      </div>
      <div class="checkbox-row">
        <label><input id="autoFit" type="checkbox" ${state.autoFit ? 'checked' : ''}> Auto-fit</label>
        <button class="button danger" id="clearTextBtn">✕</button>
        <button class="button" id="cleanBtn">${t(state.language, 'clean')}</button>
        <button class="button" id="upperBtn">${t(state.language, 'uppercase')}</button>
        <button class="button" id="lowerBtn">${t(state.language, 'lower')}</button>
        <button class="button" id="titleBtn">${t(state.language, 'titleCase')}</button>
      </div>
    </section>
  `;
}

function renderCodePanel(): string {
  const visible = state.mode === 'text_code' || state.mode === 'code' || state.mode === 'sequence_code';
  if (!visible) return '';
  return `
    <section class="card-panel">
      <h3>${t(state.language, 'codeSection')}</h3>
      <div class="grid-2">
        <div class="field"><label>${t(state.language, 'codeType')}</label><select id="codeType">${barcodeOrder.map((type) => `<option value="${type}" ${state.codeType === type ? 'selected' : ''}>${barcodeLabels[type]}</option>`).join('')}</select></div>
        <div class="field"><label>${t(state.language, 'codePosition')}</label><select id="codePosition">${positionOrder.map((pos) => `<option value="${pos}" ${state.codePosition === pos ? 'selected' : ''}>${t(state.language, pos)}</option>`).join('')}</select></div>
        ${numberField('codeArea', t(state.language, 'codeArea'), state.codeArea, 30, 260)}
        ${numberField('codeMagnification', t(state.language, 'magnification'), state.codeMagnification, 1, 10)}
      </div>
      ${state.mode !== 'sequence_code' ? `<div class="field"><label>${t(state.language, 'codeContent')}</label><input class="input" id="codeContent" value="${escapeAttr(state.codeContent)}"></div>` : ''}
      ${state.mode === 'sequence_code' ? `<div class="field"><label>${t(state.language, 'barcodeMode')}</label><select id="barcodeMode"><option value="value" ${state.sequence.barcodeMode === 'value' ? 'selected' : ''}>${t(state.language, 'value')}</option><option value="first_line" ${state.sequence.barcodeMode === 'first_line' ? 'selected' : ''}>${t(state.language, 'first_line')}</option><option value="all_text" ${state.sequence.barcodeMode === 'all_text' ? 'selected' : ''}>${t(state.language, 'all_text')}</option></select></div>` : ''}
      <div class="checkbox-row"><label><input id="showBarcodeText" type="checkbox" ${state.showBarcodeText ? 'checked' : ''}> ${t(state.language, 'humanText')}</label></div>
    </section>
  `;
}

function renderSequencePanel(): string {
  const visible = state.mode === 'sequence' || state.mode === 'sequence_code';
  if (!visible) return '';
  return `
    <section class="card-panel">
      <h3>${t(state.language, 'sequenceSettings')}</h3>
      <div class="grid-3">
        ${numberField('seqStart', t(state.language, 'start'), state.sequence.start, -999999, 999999)}
        ${numberField('seqCount', t(state.language, 'count'), state.sequence.count, 1, 500)}
        ${numberField('seqStep', t(state.language, 'step'), state.sequence.step, -9999, 9999)}
        ${numberField('seqPadding', t(state.language, 'padding'), state.sequence.padding, 0, 12)}
        <div class="field"><label>${t(state.language, 'prefix')}</label><input class="input" id="seqPrefix" value="${escapeAttr(state.sequence.prefix)}"></div>
        <div class="field"><label>${t(state.language, 'suffix')}</label><input class="input" id="seqSuffix" value="${escapeAttr(state.sequence.suffix)}"></div>
      </div>
      <div class="field"><label>${t(state.language, 'template')}</label><textarea id="seqTemplate">${escapeHtml(state.sequence.template)}</textarea></div>
      <div class="pill-row">
        <button class="pill" data-seq-preset="001">001, 002, 003</button>
        <button class="pill" data-seq-preset="asset">AS-0001</button>
        <button class="pill" data-seq-preset="cable">Cable 01</button>
        <button class="pill" data-seq-preset="year">2026-0001</button>
      </div>
    </section>
  `;
}

function renderBatchPanel(): string {
  if (state.mode !== 'batch') return '';
  return `
    <section class="card-panel">
      <h3>${t(state.language, 'batchText')}</h3>
      <p class="help">${t(state.language, 'batchHelp')}</p>
      <textarea id="batchText">${escapeHtml(state.batchText)}</textarea>
    </section>
  `;
}

function numberField(id: string, label: string, value: number, min: number, max: number): string {
  return `<div class="field"><label>${label}</label><input class="input" id="${id}" type="number" min="${min}" max="${max}" value="${value}"></div>`;
}

function selected(actual: number, expected: number): string {
  return Number(actual) === Number(expected) ? 'selected' : '';
}

function renderPreviewLabel(): string {
  const spec = buildSpec(state, sequenceValues(state)[0], state.sequence.start, 0);
  const layout = calculateLayout(spec);
  const maxW = 450;
  const maxH = 300;
  const scale = Math.min(maxW / layout.pw, maxH / layout.ll, 1.7);
  const w = Math.max(80, Math.round(layout.pw * scale));
  const h = Math.max(40, Math.round(layout.ll * scale));
  const textStyle = `left:${layout.textX * scale}px;top:${layout.textY * scale}px;width:${layout.textW * scale}px;font-size:${Math.max(9, layout.fs * scale)}px;position:absolute;`;
  const codeStyle = `left:${layout.barX * scale}px;top:${layout.barY * scale}px;width:${Math.max(30, layout.barH * scale)}px;height:${Math.max(30, layout.barH * scale)}px;position:absolute;`;
  return `
    <div class="label-preview ${spec.inverted ? 'inverted' : ''}" style="width:${w}px;height:${h}px">
      ${spec.border ? '<div class="label-border"></div>' : ''}
      <div class="label-text ${spec.alignment}" style="${textStyle}">${escapeHtml(spec.lines.filter(Boolean).join('\n'))}</div>
      ${spec.barcode && spec.barcodeText.trim() ? `<div class="code-holder" style="${codeStyle}"><canvas id="codeCanvas"></canvas></div>` : ''}
    </div>
  `;
}

function renderBarcodeCanvas(): void {
  const canvas = document.getElementById('codeCanvas') as HTMLCanvasElement | null;
  if (!canvas) return;
  const spec = buildSpec(state, sequenceValues(state)[0], state.sequence.start, 0);
  const bcid = mapBarcodeType(spec.barcodeType);
  try {
    bwipjs.toCanvas(canvas, {
      bcid,
      text: spec.barcodeText,
      scale: Math.max(1, Math.min(8, spec.barcodeMagnification)),
      height: Math.max(8, Math.round(spec.barcodeArea / 6)),
      includetext: spec.showBarcodeText && !['qrcode', 'datamatrix', 'pdf417'].includes(spec.barcodeType),
      textxalign: 'center',
      paddingwidth: 0,
      paddingheight: 0,
      backgroundcolor: 'FFFFFF',
    });
  } catch (error) {
    canvas.replaceWith(document.createTextNode(`${t(state.language, 'previewFailed')}: ${String(error)}`));
  }
}

function mapBarcodeType(type: BarcodeType): string {
  const map: Record<BarcodeType, string> = {
    code128: 'code128',
    code39: 'code39',
    ean13: 'ean13',
    upca: 'upca',
    qrcode: 'qrcode',
    datamatrix: 'datamatrix',
    pdf417: 'pdf417',
  };
  return map[type];
}

function bindEvents(): void {
  document.querySelectorAll<HTMLButtonElement>('.mode-button').forEach((button) => {
    button.addEventListener('click', () => setState({ mode: button.dataset.mode as WorkflowMode }));
  });
  bindInput('printerSelect', () => setState({ printer: stringValue('printerSelect') }));
  bindInput('language', () => setState({ language: stringValue('language', 'de') as Language }));
  bindInput('theme', () => setState({ theme: stringValue('theme', 'light') as Theme }));
  bindInput('widthMm', () => setState({ widthMm: clamp(numberValue('widthMm', state.widthMm), 1, 500) }));
  bindInput('heightMm', () => setState({ heightMm: clamp(numberValue('heightMm', state.heightMm), 1, 500) }));
  bindInput('dpi', () => setState({ dpi: numberValue('dpi', state.dpi) }));
  bindInput('copies', () => setState({ copies: clamp(numberValue('copies', state.copies), 1, 999) }));
  bindInput('border', () => setState({ border: boolValue('border') }));
  bindInput('inverted', () => setState({ inverted: boolValue('inverted') }));
  bindInput('textInput', () => state.mode === 'code' ? setState({ caption: stringValue('textInput') }) : setState({ text: stringValue('textInput') }));
  bindInput('fontSize', () => setState({ fontSize: clamp(numberValue('fontSize', state.fontSize), 8, 160) }));
  bindInput('lineGap', () => setState({ lineGap: clamp(numberValue('lineGap', state.lineGap), 0, 80) }));
  bindInput('alignment', () => setState({ alignment: stringValue('alignment', 'center') as AppState['alignment'] }));
  bindInput('autoFit', () => setState({ autoFit: boolValue('autoFit') }));
  bindInput('codeType', () => setState({ codeType: stringValue('codeType', 'qrcode') as BarcodeType }));
  bindInput('codePosition', () => setState({ codePosition: stringValue('codePosition', 'right') as CodePosition }));
  bindInput('codeArea', () => setState({ codeArea: clamp(numberValue('codeArea', state.codeArea), 30, 260) }));
  bindInput('codeMagnification', () => setState({ codeMagnification: clamp(numberValue('codeMagnification', state.codeMagnification), 1, 10) }));
  bindInput('codeContent', () => setState({ codeContent: stringValue('codeContent') }));
  bindInput('barcodeMode', () => setSequence('barcodeMode', stringValue('barcodeMode', 'value') as BarcodeMode));
  bindInput('showBarcodeText', () => setState({ showBarcodeText: boolValue('showBarcodeText') }));
  bindInput('seqStart', () => setSequence('start', numberValue('seqStart', state.sequence.start)));
  bindInput('seqCount', () => setSequence('count', clamp(numberValue('seqCount', state.sequence.count), 1, 500)));
  bindInput('seqStep', () => setSequence('step', numberValue('seqStep', state.sequence.step) || 1));
  bindInput('seqPadding', () => setSequence('padding', clamp(numberValue('seqPadding', state.sequence.padding), 0, 12)));
  bindInput('seqPrefix', () => setSequence('prefix', stringValue('seqPrefix')));
  bindInput('seqSuffix', () => setSequence('suffix', stringValue('seqSuffix')));
  bindInput('seqTemplate', () => setSequence('template', stringValue('seqTemplate')));
  bindInput('batchText', () => setState({ batchText: stringValue('batchText') }));

  click('refreshPrintersBtn', () => void refreshPrinters());
  click('refreshPreviewBtn', () => render());
  click('copyZplBtn', () => void copyZpl());
  click('exportZplBtn', () => exportZpl());
  click('printBtn', () => void sendPrint());
  click('clearTextBtn', () => setState({ text: '', caption: '', codeContent: '' }));
  click('cleanBtn', () => updateText((text) => text.replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim()));
  click('upperBtn', () => updateText((text) => text.toUpperCase()));
  click('lowerBtn', () => updateText((text) => text.toLowerCase()));
  click('titleBtn', () => updateText((text) => text.toLowerCase().replace(/\b\p{L}/gu, (char) => char.toUpperCase())));
  document.querySelectorAll<HTMLButtonElement>('[data-seq-preset]').forEach((button) => {
    button.addEventListener('click', () => applySequencePreset(button.dataset.seqPreset ?? '001'));
  });
}

function bindInput(id: string, handler: () => void): void {
  const el = document.getElementById(id);
  if (!el) return;
  const eventName = el instanceof HTMLInputElement && el.type === 'checkbox' ? 'change' : 'input';
  el.addEventListener(eventName, handler);
}

function click(id: string, handler: () => void): void {
  document.getElementById(id)?.addEventListener('click', handler);
}

function updateText(fn: (text: string) => string): void {
  if (state.mode === 'code') setState({ caption: fn(state.caption) });
  else setState({ text: fn(state.text) });
}

function applySequencePreset(name: string): void {
  if (name === 'asset') {
    state.sequence = { ...state.sequence, start: 1, padding: 4, prefix: 'AS-', suffix: '', template: 'Asset {value}' };
  } else if (name === 'cable') {
    state.sequence = { ...state.sequence, start: 1, padding: 2, prefix: 'Cable ', suffix: '', template: '{value}\nDestination' };
  } else if (name === 'year') {
    state.sequence = { ...state.sequence, start: 1, padding: 4, prefix: '2026-', suffix: '', template: '{value}' };
  } else {
    state.sequence = { ...state.sequence, start: 1, padding: 3, prefix: '', suffix: '', template: '{value}' };
  }
  saveState();
  render();
}

function currentZpl(): string {
  try {
    return generateOutputZpl(state);
  } catch (error) {
    return `error: ${String(error)}`;
  }
}

async function refreshPrinters(): Promise<void> {
  const printers = await listPrinters();
  setState({ printers, printer: state.printer || printers[0] || '' });
  status(printers.length ? t(state.language, 'ready') : t(state.language, 'noPrinter'), printers.length ? 'ok' : '');
}

async function copyZpl(): Promise<void> {
  await navigator.clipboard.writeText(currentZpl());
  status(t(state.language, 'copied'), 'ok');
}

function exportZpl(): void {
  const blob = new Blob([currentZpl()], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = state.mode === 'sequence' || state.mode === 'sequence_code' || state.mode === 'batch' ? 'labels.zpl' : 'label.zpl';
  a.click();
  URL.revokeObjectURL(url);
  status(t(state.language, 'exported'), 'ok');
}

async function sendPrint(): Promise<void> {
  if (!state.printer) {
    status(t(state.language, 'noPrinter'), 'error');
    return;
  }
  try {
    await printZpl(state.printer, currentZpl());
    status(t(state.language, 'printSent'), 'ok');
  } catch (error) {
    status(`${t(state.language, 'printFailed')}: ${String(error)}`, 'error');
  }
}

function status(message: string, kind: 'ok' | 'error' | '' = ''): void {
  const box = document.getElementById('statusBox');
  if (!box) return;
  box.textContent = message;
  box.className = `status ${kind}`.trim();
}

function summaryText(): string {
  const parts = [`${state.widthMm} × ${state.heightMm} mm`, `${state.dpi} dpi`];
  if (state.mode === 'sequence' || state.mode === 'sequence_code') parts.push(`${state.sequence.count} labels`);
  if (state.mode === 'batch') parts.push(`${state.batchText.split(/\n\s*\n/g).filter((block) => block.trim()).length} labels`);
  return parts.join(' · ');
}

function escapeHtml(value: string): string {
  return String(value ?? '').replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char] ?? char));
}

function escapeAttr(value: string): string {
  return escapeHtml(value).replace(/'/g, '&#39;');
}

render();
void refreshPrinters();
