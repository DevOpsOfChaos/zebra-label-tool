import bwipjs from 'bwip-js';
import './styles.css';
import { listPrinters, printZpl } from './bridge';
import {
  barcodeLabels,
  barcodeOrder,
  modeOrder,
  positionOrder,
  sequenceKindOrder,
  type AppState,
  type BarcodeMode,
  type Density,
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
  density: 'compact',
  sidebarCollapsed: false,
  showZplPanel: false,
  previewZoom: 1,
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
    kind: 'number',
    start: 1,
    letterStart: 'A',
    count: 10,
    step: 1,
    padding: 3,
    prefix: 'AS-',
    suffix: '',
    template: 'Asset {value}\nRack A',
    barcodeMode: 'value',
    barcodeTemplate: 'asset:{value}',
    valuePattern: '{letter}-{number}',
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

function render(): void {
  document.body.classList.toggle('dark', state.theme === 'dark');
  document.body.classList.toggle('compact', state.density === 'compact');
  const app = document.getElementById('app');
  if (!app) return;
  app.innerHTML = `
    <main class="app-shell ${state.sidebarCollapsed ? 'nav-collapsed' : ''}">
      <aside class="sidebar ${state.sidebarCollapsed ? 'collapsed' : ''}">
        <div class="brand-row">
          ${state.sidebarCollapsed ? '' : `<div class="brand"><h1>${t(state.language, 'appTitle')}</h1><p>${t(state.language, 'appSubtitle')}</p></div>`}
          <button class="button icon-button" id="toggleSidebarBtn" title="${t(state.language, 'toggleSidebar')}">${state.sidebarCollapsed ? '›' : '‹'}</button>
        </div>
        ${state.sidebarCollapsed ? '' : `
          <div class="mode-list" aria-label="${t(state.language, 'mode')}">
            ${modeOrder.map(modeButton).join('')}
          </div>
          <div class="settings-stack">
            ${renderPrinterSettings()}
            ${renderLabelSettings()}
            ${renderAppSettings()}
          </div>
        `}
      </aside>
      <section class="workspace">
        <div class="toolbar compact-toolbar">
          <div class="toolbar-title">
            <h2>${modeLabel(state.language, state.mode)}</h2>
          </div>
          <div class="toolbar-actions">
            <button class="button primary" id="printBtn">${t(state.language, 'print')}</button>
          </div>
        </div>
        ${renderTextPanel()}
        ${renderCodePanel()}
        ${renderSequencePanel()}
        ${renderBatchPanel()}
        ${renderTemplatesPanel()}
      </section>
      <aside class="preview-pane">
        <div class="preview-header">
          <div>
            <h2>${t(state.language, 'preview')}</h2>
            <p>${summaryText()}</p>
          </div>
          <div class="preview-tools">
            <button class="button ghost" id="copyZplBtn">${t(state.language, 'copyZplShort')}</button>
            <button class="button ghost" id="exportZplBtn">${t(state.language, 'exportZplShort')}</button>
            <button class="button ghost" id="zoomOutBtn" title="${t(state.language, 'zoomOut')}">−</button>
            <button class="button ghost" id="fitPreviewBtn" title="${t(state.language, 'fitPreview')}">Fit</button>
            <button class="button ghost" id="zoomInBtn" title="${t(state.language, 'zoomIn')}">+</button>
            <button class="button ghost" id="toggleZplBtn">${state.showZplPanel ? t(state.language, 'hideZpl') : t(state.language, 'showZpl')}</button>
            <button class="button ghost" id="refreshPreviewBtn">↻</button>
          </div>
        </div>
        <div class="preview-stage">
          ${renderPreviewLabel()}
        </div>
        <div class="status" id="statusBox">${t(state.language, 'ready')}</div>
        ${state.showZplPanel ? `<textarea class="zpl-box" id="zplBox" spellcheck="false">${escapeHtml(currentZpl())}</textarea>` : `<div class="zpl-collapsed">${t(state.language, 'zplHiddenHint')}</div>`}
      </aside>
    </main>
  `;
  bindEvents();
  renderBarcodeCanvas();
}

function modeButton(mode: WorkflowMode): string {
  return `
    <button class="mode-button ${state.mode === mode ? 'active' : ''}" data-mode="${mode}" title="${modeLabel(state.language, mode)}">
      <strong>${modeLabel(state.language, mode)}</strong>
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
        <div class="field"><label>${t(state.language, 'density')}</label><select id="density"><option value="compact" ${state.density === 'compact' ? 'selected' : ''}>${t(state.language, 'compact')}</option><option value="comfortable" ${state.density === 'comfortable' ? 'selected' : ''}>${t(state.language, 'comfortable')}</option></select></div>
      </div>
    </details>
  `;
}

function renderTextPanel(): string {
  const visible = state.mode === 'text' || state.mode === 'text_code' || state.mode === 'sequence' || state.mode === 'sequence_code';
  if (!visible) return '';
  return `
    <section class="card-panel compact-section">
      <div class="section-head">
        <h3>${t(state.language, 'labelText')}</h3>
        <button class="button danger micro" id="clearTextBtn" title="${t(state.language, 'clearContent')}">✕</button>
      </div>
      <textarea id="textInput" spellcheck="false">${escapeHtml(state.text)}</textarea>
      <details class="inline-advanced">
        <summary>${t(state.language, 'textOptions')}</summary>
        <div class="grid-3 compact-grid">
          ${numberField('fontSize', t(state.language, 'font'), state.fontSize, 8, 160)}
          ${numberField('lineGap', t(state.language, 'lineGap'), state.lineGap, 0, 80)}
          <div class="field"><label>${t(state.language, 'alignment')}</label><select id="alignment"><option value="left" ${state.alignment === 'left' ? 'selected' : ''}>${t(state.language, 'left')}</option><option value="center" ${state.alignment === 'center' ? 'selected' : ''}>${t(state.language, 'center')}</option><option value="right" ${state.alignment === 'right' ? 'selected' : ''}>${t(state.language, 'right')}</option></select></div>
        </div>
        <div class="checkbox-row tight-row">
          <label><input id="autoFit" type="checkbox" ${state.autoFit ? 'checked' : ''}> ${t(state.language, 'autoFit')}</label>
        </div>
      </details>
      <details class="inline-advanced">
        <summary>${t(state.language, 'moreTextTools')}</summary>
        <div class="pill-row">
          <button class="button" id="cleanBtn">${t(state.language, 'clean')}</button>
          <button class="button" id="upperBtn">${t(state.language, 'uppercase')}</button>
          <button class="button" id="lowerBtn">${t(state.language, 'lower')}</button>
          <button class="button" id="titleBtn">${t(state.language, 'titleCase')}</button>
          <button class="button" id="trimBtn">${t(state.language, 'trimLines')}</button>
          <button class="button" id="dedupeBtn">${t(state.language, 'dedupeLines')}</button>
          <button class="button" id="sampleTextBtn">${t(state.language, 'sampleText')}</button>
        </div>
      </details>
    </section>
  `;
}

function renderCodePanel(): string {
  const visible = state.mode === 'text_code' || state.mode === 'code' || state.mode === 'sequence_code';
  if (!visible) return '';
  return `
    <section class="card-panel compact-section">
      <h3>${t(state.language, 'codeSection')}</h3>
      <div class="grid-2 compact-grid">
        <div class="field"><label>${t(state.language, 'codeType')}</label><select id="codeType">${barcodeOrder.map((type) => `<option value="${type}" ${state.codeType === type ? 'selected' : ''}>${barcodeLabels[type]}</option>`).join('')}</select></div>
        <div class="field"><label>${t(state.language, 'codePosition')}</label><select id="codePosition">${positionOrder.map((pos) => `<option value="${pos}" ${state.codePosition === pos ? 'selected' : ''}>${t(state.language, pos)}</option>`).join('')}</select></div>
      </div>
      ${state.mode !== 'sequence_code' ? `<div class="field"><label>${t(state.language, 'codeContent')}</label><input class="input" id="codeContent" value="${escapeAttr(state.codeContent)}"></div>` : ''}
      <details class="inline-advanced">
        <summary>${t(state.language, 'codeOptions')}</summary>
        <div class="grid-2 compact-grid">
          ${numberField('codeArea', t(state.language, 'codeArea'), state.codeArea, 30, 320)}
          ${numberField('codeMagnification', t(state.language, 'magnification'), state.codeMagnification, 1, 12)}
        </div>
        <div class="pill-row compact-pills" aria-label="${t(state.language, 'codeSize')}">
          <span class="inline-label">${t(state.language, 'codeSize')}</span>
          <button class="pill" data-code-size="small">S</button>
          <button class="pill" data-code-size="medium">M</button>
          <button class="pill" data-code-size="large">L</button>
          <button class="pill" data-code-size="xl">XL</button>
          <button class="pill ${state.codePosition === 'center' ? 'active' : ''}" data-code-center="1">${t(state.language, 'centerCode')}</button>
        </div>
        <div class="checkbox-row tight-row"><label><input id="showBarcodeText" type="checkbox" ${state.showBarcodeText ? 'checked' : ''}> ${t(state.language, 'humanText')}</label></div>
        <div class="pill-row">
          <button class="button" id="codeFromFirstLineBtn">${t(state.language, 'useFirstLine')}</button>
          <button class="button" id="codeFromAllTextBtn">${t(state.language, 'useAllText')}</button>
          <button class="button" id="sampleQrBtn">${t(state.language, 'sampleQr')}</button>
        </div>
      </details>
    </section>
  `;
}

function renderSequencePanel(): string {
  const visible = state.mode === 'sequence' || state.mode === 'sequence_code';
  if (!visible) return '';
  return `
    <section class="card-panel compact-section">
      <h3>${t(state.language, 'sequenceSettings')}</h3>
      <div class="grid-3 compact-grid">
        <div class="field"><label>${t(state.language, 'sequenceKind')}</label><select id="seqKind">${sequenceKindOrder.map((kind) => `<option value="${kind}" ${state.sequence.kind === kind ? 'selected' : ''}>${kind === 'letters' ? t(state.language, 'letterSequence') : kind === 'mixed' ? t(state.language, 'mixedSequence') : t(state.language, 'numberSequence')}</option>`).join('')}</select></div>
        ${numberField('seqCount', t(state.language, 'count'), state.sequence.count, 1, 500)}
        ${state.sequence.kind === 'mixed' ? `<div class="field"><label>${t(state.language, 'valuePattern')}</label><input class="input" id="seqValuePattern" value="${escapeAttr(state.sequence.valuePattern)}"></div>` : ''}
      </div>
      <div class="field"><label>${t(state.language, 'template')}</label><textarea id="seqTemplate">${escapeHtml(state.sequence.template)}</textarea></div>
      ${state.mode === 'sequence_code' ? `<details class="inline-advanced" open><summary>${t(state.language, 'sequenceCodeOptions')}</summary><div class="grid-2 compact-grid"><div class="field"><label>${t(state.language, 'barcodeMode')}</label><select id="barcodeMode"><option value="value" ${state.sequence.barcodeMode === 'value' ? 'selected' : ''}>${t(state.language, 'value')}</option><option value="first_line" ${state.sequence.barcodeMode === 'first_line' ? 'selected' : ''}>${t(state.language, 'first_line')}</option><option value="all_text" ${state.sequence.barcodeMode === 'all_text' ? 'selected' : ''}>${t(state.language, 'all_text')}</option><option value="template" ${state.sequence.barcodeMode === 'template' ? 'selected' : ''}>${t(state.language, 'templateMode')}</option></select></div><div class="field"><label>${t(state.language, 'barcodeTemplate')}</label><input class="input" id="seqBarcodeTemplate" value="${escapeAttr(state.sequence.barcodeTemplate)}"></div></div></details>` : ''}
      <div class="sequence-preview"><strong>${t(state.language, 'nextValues')}</strong><span>${sequenceValues(state).slice(0, 5).map(escapeHtml).join(' · ')}</span></div>
      <details class="inline-advanced">
        <summary>${t(state.language, 'sequenceOptions')}</summary>
        <div class="grid-3 compact-grid">
          ${state.sequence.kind !== 'letters' ? numberField('seqStart', t(state.language, 'start'), state.sequence.start, -999999, 999999) : ''}
          ${state.sequence.kind !== 'number' ? `<div class="field"><label>${t(state.language, 'letterStart')}</label><input class="input" id="seqLetterStart" value="${escapeAttr(state.sequence.letterStart)}"></div>` : ''}
          ${numberField('seqStep', t(state.language, 'step'), state.sequence.step, -9999, 9999)}
          ${state.sequence.kind !== 'letters' ? numberField('seqPadding', t(state.language, 'padding'), state.sequence.padding, 0, 12) : ''}
          <div class="field"><label>${t(state.language, 'prefix')}</label><input class="input" id="seqPrefix" value="${escapeAttr(state.sequence.prefix)}"></div>
          <div class="field"><label>${t(state.language, 'suffix')}</label><input class="input" id="seqSuffix" value="${escapeAttr(state.sequence.suffix)}"></div>
        </div>
      </details>
      <details class="inline-advanced">
        <summary>${t(state.language, 'sequencePresets')}</summary>
        <div class="pill-row" aria-label="${t(state.language, 'sequencePresets')}">
          <button class="pill" data-seq-preset="001">001, 002, 003</button>
          <button class="pill" data-seq-preset="asset">AS-0001</button>
          <button class="pill" data-seq-preset="letters">A, B, C</button>
          <button class="pill" data-seq-preset="rack">Rack-A</button>
          <button class="pill" data-seq-preset="mixed">A-001</button>
          <button class="pill" data-seq-preset="cable">Cable 01</button>
          <button class="pill" data-seq-preset="year">2026-0001</button>
        </div>
      </details>
    </section>
  `;
}

function renderTemplatesPanel(): string {
  return `
    <details class="card-panel template-panel">
      <summary>${t(state.language, 'templates')}</summary>
      <div class="template-grid">
        <button class="pill" data-template="device_qr">${t(state.language, 'tplDeviceQr')}</button>
        <button class="pill" data-template="asset_qr">${t(state.language, 'tplAssetQr')}</button>
        <button class="pill" data-template="wifi_qr">${t(state.language, 'tplWifiQr')}</button>
        <button class="pill" data-template="shelf_box">${t(state.language, 'tplShelfBox')}</button>
        <button class="pill" data-template="cable_marker">${t(state.language, 'tplCableMarker')}</button>
        <button class="pill" data-template="maintenance">${t(state.language, 'tplMaintenance')}</button>
        <button class="pill" data-template="shipping">${t(state.language, 'tplShipping')}</button>
      </div>
    </details>
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
  const spec = buildSpec(state);
  const layout = calculateLayout(spec);
  const maxW = state.sidebarCollapsed ? 650 : 470;
  const maxH = state.sidebarCollapsed ? 390 : 300;
  const baseScale = Math.min(maxW / layout.pw, maxH / layout.ll, 1.55);
  const scale = Math.max(0.25, Math.min(2.2, baseScale * state.previewZoom));
  const w = Math.max(80, Math.round(layout.pw * scale));
  const h = Math.max(40, Math.round(layout.ll * scale));
  const textStyle = `left:${layout.textX * scale}px;top:${layout.textY * scale}px;width:${layout.textW * scale}px;font-size:${Math.max(9, layout.fs * scale)}px;position:absolute;`;
  const codeStyle = `left:${layout.barX * scale}px;top:${layout.barY * scale}px;width:${Math.max(30, layout.barW * scale)}px;height:${Math.max(30, layout.barH * scale)}px;position:absolute;`;
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
  const spec = buildSpec(state);
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
  bindInput('density', () => setState({ density: stringValue('density', 'compact') as Density }));
  bindInput('widthMm', () => setState({ widthMm: clamp(numberValue('widthMm', state.widthMm), 1, 500) }));
  bindInput('heightMm', () => setState({ heightMm: clamp(numberValue('heightMm', state.heightMm), 1, 500) }));
  bindInput('dpi', () => setState({ dpi: numberValue('dpi', state.dpi) }));
  bindInput('copies', () => setState({ copies: clamp(numberValue('copies', state.copies), 1, 999) }));
  bindInput('border', () => setState({ border: boolValue('border') }));
  bindInput('inverted', () => setState({ inverted: boolValue('inverted') }));
  bindInput('textInput', () => setState({ text: stringValue('textInput') }));
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
  bindInput('seqBarcodeTemplate', () => setSequence('barcodeTemplate', stringValue('seqBarcodeTemplate', state.sequence.barcodeTemplate)));
  bindInput('seqValuePattern', () => setSequence('valuePattern', stringValue('seqValuePattern', state.sequence.valuePattern)));
  bindInput('showBarcodeText', () => setState({ showBarcodeText: boolValue('showBarcodeText') }));
  bindInput('seqKind', () => setSequence('kind', stringValue('seqKind', 'number') as AppState['sequence']['kind']));
  bindInput('seqStart', () => setSequence('start', numberValue('seqStart', state.sequence.start)));
  bindInput('seqLetterStart', () => setSequence('letterStart', stringValue('seqLetterStart', state.sequence.letterStart).toUpperCase()));
  bindInput('seqCount', () => setSequence('count', clamp(numberValue('seqCount', state.sequence.count), 1, 500)));
  bindInput('seqStep', () => setSequence('step', numberValue('seqStep', state.sequence.step) || 1));
  bindInput('seqPadding', () => setSequence('padding', clamp(numberValue('seqPadding', state.sequence.padding), 0, 12)));
  bindInput('seqPrefix', () => setSequence('prefix', stringValue('seqPrefix')));
  bindInput('seqSuffix', () => setSequence('suffix', stringValue('seqSuffix')));
  bindInput('seqTemplate', () => setSequence('template', stringValue('seqTemplate')));
  bindInput('batchText', () => setState({ batchText: stringValue('batchText') }));

  click('toggleSidebarBtn', () => setState({ sidebarCollapsed: !state.sidebarCollapsed }));
  click('refreshPrintersBtn', () => void refreshPrinters());
  click('refreshPreviewBtn', () => render());
  click('toggleZplBtn', () => setState({ showZplPanel: !state.showZplPanel }));
  click('fitPreviewBtn', () => setState({ previewZoom: 1 }));
  click('zoomOutBtn', () => setState({ previewZoom: clamp(state.previewZoom - 0.1, 0.6, 1.8) }));
  click('zoomInBtn', () => setState({ previewZoom: clamp(state.previewZoom + 0.1, 0.6, 1.8) }));
  click('copyZplBtn', () => void copyZpl());
  click('exportZplBtn', () => exportZpl());
  click('printBtn', () => void sendPrint());
  click('clearTextBtn', () => setState({ text: '', caption: '', codeContent: '' }));
  click('cleanBtn', () => updateText((text) => text.replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim()));
  click('upperBtn', () => updateText((text) => text.toUpperCase()));
  click('lowerBtn', () => updateText((text) => text.toLowerCase()));
  click('titleBtn', () => updateText((text) => text.toLowerCase().replace(/\b\p{L}/gu, (char) => char.toUpperCase())));
  click('trimBtn', () => updateText((text) => text.split(/\r?\n/).map((line) => line.trim()).join('\n')));
  click('dedupeBtn', () => updateText((text) => Array.from(new Set(text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean))).join('\n')));
  click('sampleTextBtn', () => setState({ text: state.language === 'de' ? 'Gerät\nESP32-Küche' : 'Device\nESP32-Kitchen' }));
  click('codeFromFirstLineBtn', () => setState({ codeContent: cleanLines(state.text).find((line) => line.trim()) ?? state.codeContent }));
  click('codeFromAllTextBtn', () => setState({ codeContent: cleanLines(state.text).filter((line) => line.trim()).join(' | ') }));
  click('sampleQrBtn', () => setState({ codeType: 'qrcode', codeContent: 'https://example.local/device/1', codePosition: 'right', codeArea: 120, codeMagnification: 5 }));
  document.querySelectorAll<HTMLButtonElement>('[data-template]').forEach((button) => {
    button.addEventListener('click', () => applyTemplate(button.dataset.template ?? 'device_qr'));
  });
  document.querySelectorAll<HTMLButtonElement>('[data-code-size]').forEach((button) => {
    button.addEventListener('click', () => applyCodeSize(button.dataset.codeSize ?? 'medium'));
  });
  document.querySelectorAll<HTMLButtonElement>('[data-code-center]').forEach((button) => {
    button.addEventListener('click', () => setState({ codePosition: 'center' }));
  });
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
  setState({ text: fn(state.text) });
}


function applyTemplate(name: string): void {
  if (name === 'device_qr') {
    setState({ mode: 'text_code', widthMm: 57, heightMm: 25, text: 'Device\nESP32-Kitchen', codeType: 'qrcode', codeContent: 'https://example.local/device/esp32-kitchen', codePosition: 'right', codeArea: 120, codeMagnification: 5, fontSize: 42, alignment: 'left', border: false });
  } else if (name === 'asset_qr') {
    setState({ mode: 'text_code', widthMm: 62, heightMm: 29, text: 'Asset AS-0001\nRack A', codeType: 'qrcode', codeContent: 'asset:AS-0001', codePosition: 'right', codeArea: 115, codeMagnification: 5, fontSize: 38, alignment: 'left', border: true });
  } else if (name === 'wifi_qr') {
    setState({ mode: 'text_code', widthMm: 70, heightMm: 35, text: 'Wi-Fi\nWorkshop', codeType: 'qrcode', codeContent: 'WIFI:T:WPA;S:Workshop;P:change-me;;', codePosition: 'right', codeArea: 135, codeMagnification: 5, fontSize: 36, alignment: 'left', border: true });
  } else if (name === 'shelf_box') {
    setState({ mode: 'text', widthMm: 57, heightMm: 19, text: 'Shelf A\nBox 01', codeContent: '', fontSize: 50, alignment: 'center', border: true });
  } else if (name === 'cable_marker') {
    setState({ mode: 'sequence_code', widthMm: 57, heightMm: 19, codeType: 'code128', codePosition: 'below', codeArea: 55, codeMagnification: 3, fontSize: 30, alignment: 'center', sequence: { ...state.sequence, kind: 'mixed', count: 12, padding: 2, letterStart: 'A', start: 1, prefix: '', suffix: '', valuePattern: 'CB-{letter}-{number:00}', template: '{value}\nCable', barcodeMode: 'value', barcodeTemplate: '{value}' } });
  } else if (name === 'maintenance') {
    setState({ mode: 'text_code', widthMm: 70, heightMm: 30, text: 'Service\nNext check', codeType: 'qrcode', codeContent: 'service:next-check', codePosition: 'right', codeArea: 120, codeMagnification: 5, fontSize: 36, alignment: 'left', border: true });
  } else if (name === 'shipping') {
    setState({ mode: 'text_code', widthMm: 100, heightMm: 50, text: 'Package\nOrder 1001', codeType: 'code128', codeContent: 'ORDER-1001', codePosition: 'below', codeArea: 80, codeMagnification: 3, fontSize: 50, alignment: 'center', border: true });
  }
}

function applyCodeSize(size: string): void {
  const presets: Record<string, Pick<AppState, 'codeArea' | 'codeMagnification'>> = {
    small: { codeArea: 70, codeMagnification: 3 },
    medium: { codeArea: 110, codeMagnification: 5 },
    large: { codeArea: 160, codeMagnification: 7 },
    xl: { codeArea: 220, codeMagnification: 9 },
  };
  setState(presets[size] ?? presets.medium);
}

function applySequencePreset(name: string): void {
  if (name === 'asset') {
    state.sequence = { ...state.sequence, kind: 'number', start: 1, padding: 4, prefix: 'AS-', suffix: '', template: 'Asset {value}', barcodeMode: 'value', barcodeTemplate: 'asset:{value}', valuePattern: '{letter}-{number}' };
  } else if (name === 'letters') {
    state.sequence = { ...state.sequence, kind: 'letters', letterStart: 'A', step: 1, prefix: '', suffix: '', template: 'Box {value}', barcodeMode: 'template', barcodeTemplate: 'box-{value}', valuePattern: '{letter}-{number}' };
  } else if (name === 'rack') {
    state.sequence = { ...state.sequence, kind: 'letters', letterStart: 'A', step: 1, prefix: 'Rack-', suffix: '', template: '{value}\nShelf {index}', barcodeMode: 'value', barcodeTemplate: '{value}', valuePattern: '{letter}-{number}' };
  } else if (name === 'mixed') {
    state.sequence = { ...state.sequence, kind: 'mixed', start: 1, letterStart: 'A', step: 1, padding: 3, prefix: '', suffix: '', valuePattern: '{letter}-{number}', template: 'Item {value}', barcodeMode: 'template', barcodeTemplate: 'asset:{letter}-{number}' };
  } else if (name === 'cable') {
    state.sequence = { ...state.sequence, kind: 'number', start: 1, padding: 2, prefix: 'Cable ', suffix: '', template: '{value}\nDestination', barcodeMode: 'first_line', barcodeTemplate: '{value}', valuePattern: '{letter}-{number}' };
  } else if (name === 'year') {
    state.sequence = { ...state.sequence, kind: 'number', start: 1, padding: 4, prefix: '2026-', suffix: '', template: '{value}', barcodeMode: 'value', barcodeTemplate: 'serial:{value}', valuePattern: '{letter}-{number}' };
  } else {
    state.sequence = { ...state.sequence, kind: 'number', start: 1, padding: 3, prefix: '', suffix: '', template: '{value}', barcodeMode: 'value', barcodeTemplate: '{value}', valuePattern: '{letter}-{number}' };
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
