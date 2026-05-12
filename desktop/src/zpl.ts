import type { Alignment, AppState, BarcodeMode, BarcodeType, CodePosition, SequenceState } from './domain';

export interface LabelSpec {
  lines: string[];
  widthMm: number;
  heightMm: number;
  dpi: number;
  copies: number;
  border: boolean;
  inverted: boolean;
  fontSize: number;
  alignment: Alignment;
  autoFit: boolean;
  lineGap: number;
  barcode: boolean;
  barcodeType: BarcodeType;
  barcodeText: string;
  barcodePosition: CodePosition;
  barcodeArea: number;
  barcodeMagnification: number;
  showBarcodeText: boolean;
}

export interface SequenceValue {
  value: string;
  raw: number;
  index: number;
  number: string;
  letter: string;
}

export function mmToDots(mm: number, dpi: number): number {
  return Math.round((Number(mm) * Number(dpi)) / 25.4);
}

export function cleanLines(text: string): string[] {
  const lines = String(text ?? '')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .split('\n')
    .map((line) => line.trimEnd());
  const trimmed = lines.filter((line) => line.trim().length > 0);
  return trimmed.length > 0 ? trimmed.slice(0, 12) : [''];
}

export function zplEscape(value: string): string {
  return String(value ?? '').replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '');
}

function alignmentCode(alignment: Alignment): string {
  if (alignment === 'left') return 'L';
  if (alignment === 'right') return 'R';
  return 'C';
}

function codeHeight(spec: LabelSpec): number {
  const base = Math.max(24, Math.min(260, Math.round(spec.barcodeArea || 80)));
  if (['qrcode', 'datamatrix'].includes(spec.barcodeType)) {
    return Math.max(base, spec.barcodeMagnification * 18);
  }
  return base;
}

export function calculateLayout(spec: LabelSpec) {
  const pw = Math.max(1, mmToDots(spec.widthMm, spec.dpi));
  const ll = Math.max(1, mmToDots(spec.heightMm, spec.dpi));
  const margin = 16;
  const gap = 10;
  const codeActive = spec.barcode && spec.barcodeText.trim().length > 0;
  const barH = codeHeight(spec);
  const barW = Math.min(Math.max(barH, Math.round(spec.barcodeArea)), Math.max(32, pw - margin * 2));
  let textX = margin;
  let textY = 4;
  let textW = Math.max(1, pw - margin * 2);
  let barX = Math.round((pw - barW) / 2);
  let barY = Math.round((ll - barH) / 2);

  const visibleLines = spec.lines.filter((line) => line.trim().length > 0);
  const lineCount = Math.max(1, visibleLines.length || spec.lines.length);
  let fs = Math.max(8, Math.round(spec.fontSize));
  if (spec.autoFit) {
    const longest = Math.max(...spec.lines.map((line) => line.length), 1);
    const maxChars = spec.barcodePosition === 'left' || spec.barcodePosition === 'right' ? 18 : 28;
    if (longest > maxChars) fs = Math.max(8, Math.floor((fs * maxChars) / longest));
  }
  const hasVisibleText = visibleLines.length > 0;
  const textH = hasVisibleText ? fs * lineCount + Math.max(0, spec.lineGap) * Math.max(0, lineCount - 1) : 0;

  if (!codeActive) {
    textY = Math.max(4, Math.round((ll - textH) / 2));
  } else if (spec.barcodePosition === 'right') {
    textW = Math.max(1, pw - margin * 2 - barW - gap);
    textX = margin;
    textY = Math.max(4, Math.round((ll - textH) / 2));
    barX = margin + textW + gap;
    barY = Math.max(2, Math.round((ll - barH) / 2));
  } else if (spec.barcodePosition === 'left') {
    barX = margin;
    barY = Math.max(2, Math.round((ll - barH) / 2));
    textX = margin + barW + gap;
    textW = Math.max(1, pw - textX - margin);
    textY = Math.max(4, Math.round((ll - textH) / 2));
  } else if (spec.barcodePosition === 'center') {
    barX = Math.max(2, Math.round((pw - barW) / 2));
    barY = Math.max(2, Math.round((ll - barH - (hasVisibleText ? gap + textH : 0)) / 2));
    textX = margin;
    textW = Math.max(1, pw - margin * 2);
    textY = Math.min(Math.max(4, barY + barH + gap), Math.max(4, ll - textH - 4));
  } else if (spec.barcodePosition === 'above') {
    barX = Math.max(2, Math.round((pw - barW) / 2));
    barY = 4;
    textY = Math.max(barY + barH + gap, Math.round((ll - textH) / 2));
  } else {
    textY = Math.max(4, Math.round((ll - barH - gap - textH) / 2));
    barX = Math.max(2, Math.round((pw - barW) / 2));
    barY = Math.min(Math.max(2, textY + textH + gap), Math.max(2, ll - barH - 4));
  }

  return { pw, ll, margin, fs, textX, textY, textW, barX, barY, barH, barW };
}

function barcodeLines(spec: LabelSpec, x: number, y: number, h: number): string[] {
  const text = zplEscape(spec.barcodeText.trim());
  const human = spec.showBarcodeText ? 'Y' : 'N';
  switch (spec.barcodeType) {
    case 'code39':
      return [`^FO${x},${y}`, `^B3N,N,${h},${human},N`, `^FD${text}^FS`];
    case 'ean13':
      return [`^FO${x},${y}`, `^BEN,${h},${human},N`, `^FD${text}^FS`];
    case 'upca':
      return [`^FO${x},${y}`, `^BUN,${h},${human},N`, `^FD${text}^FS`];
    case 'qrcode':
      return [`^FO${x},${y}`, `^BQN,2,${spec.barcodeMagnification}`, `^FDLA,${text}^FS`];
    case 'datamatrix':
      return [`^FO${x},${y}`, `^BXN,${spec.barcodeMagnification},200`, `^FD${text}^FS`];
    case 'pdf417':
      return [`^FO${x},${y}`, `^B7N,${h},5,4,8,N`, `^FD${text}^FS`];
    case 'code128':
    default:
      return [`^FO${x},${y}`, `^BCN,${h},${human},N,N`, `^FD${text}^FS`];
  }
}

export function generateZpl(spec: LabelSpec): string {
  const layout = calculateLayout(spec);
  const zpl = ['^XA', `^PW${layout.pw}`, `^LL${layout.ll}`, '^LH0,0'];
  if (spec.copies > 1) zpl.push(`^PQ${Math.max(1, Math.round(spec.copies))},0,1,Y`);
  if (spec.inverted) zpl.push(`^FO0,0^GB${layout.pw},${layout.ll},${layout.ll}^FS`);
  if (spec.border) zpl.push(`^FO2,2^GB${layout.pw - 4},${layout.ll - 4},2^FS`);
  const text = spec.lines.map(zplEscape).join('\\&');
  if (text.trim()) {
    const inv = spec.inverted ? '^FR' : '';
    zpl.push(
      `^FO${layout.textX},${layout.textY}`,
      `^A0N,${layout.fs},${layout.fs}`,
      `^FB${layout.textW},${Math.max(1, spec.lines.length)},${Math.max(0, spec.lineGap)},${alignmentCode(spec.alignment)},0`,
      `${inv}^FD${text}^FS`,
    );
  }
  if (spec.barcode && spec.barcodeText.trim()) {
    zpl.push(...barcodeLines(spec, layout.barX, layout.barY, layout.barH));
  }
  zpl.push('^XZ');
  return zpl.join('\n');
}

function normalizeLetters(value: string): string {
  return String(value || 'A').replace(/[^a-z]/gi, '').toUpperCase() || 'A';
}

export function lettersToIndex(value: string): number {
  return normalizeLetters(value).split('').reduce((acc, char) => acc * 26 + (char.charCodeAt(0) - 64), 0);
}

export function indexToLetters(index: number): string {
  let n = Math.max(1, Math.round(index));
  let out = '';
  while (n > 0) {
    n -= 1;
    out = String.fromCharCode(65 + (n % 26)) + out;
    n = Math.floor(n / 26);
  }
  return out;
}

export function formatNumberValue(raw: number, padding: number, prefix: string, suffix: string): string {
  const sign = raw < 0 ? '-' : '';
  return `${prefix}${sign}${Math.abs(Math.round(raw)).toString().padStart(Math.max(0, padding), '0')}${suffix}`;
}

function paddedNumber(raw: number, padding: number): string {
  const sign = raw < 0 ? '-' : '';
  return `${sign}${Math.abs(Math.round(raw)).toString().padStart(Math.max(0, padding), '0')}`;
}

function replaceSequenceTokens(template: string, item: SequenceValue): string {
  return String(template || '{value}')
    .replace(/\{(?:n|number)(?::(0+|\d+))?\}/g, (_match, width: string | undefined) => {
      if (!width) return item.number;
      const digits = /^0+$/.test(width) ? width.length : Number(width);
      return paddedNumber(item.raw, Number.isFinite(digits) ? Number(digits) : 0);
    })
    .replaceAll('{value}', item.value)
    .replaceAll('{seq}', item.value)
    .replaceAll('{letter}', item.letter)
    .replaceAll('{letters}', item.letter)
    .replaceAll('{raw}', String(item.raw))
    .replaceAll('{index}', String(item.index + 1))
    .replaceAll('{index0}', String(item.index));
}

export function formatSequenceItem(sequence: SequenceState, index: number): SequenceValue {
  const raw = sequence.start + index * sequence.step;
  const letterRaw = lettersToIndex(sequence.letterStart) + index * sequence.step;
  const number = paddedNumber(raw, sequence.padding);
  const letter = indexToLetters(letterRaw);
  if (sequence.kind === 'letters') {
    return { value: `${sequence.prefix}${letter}${sequence.suffix}`, raw: letterRaw, index, number, letter };
  }
  if (sequence.kind === 'mixed') {
    const item = { value: '', raw, index, number, letter };
    const core = replaceSequenceTokens(sequence.valuePattern || '{letter}-{number}', item);
    return { value: `${sequence.prefix}${core}${sequence.suffix}`, raw, index, number, letter };
  }
  return { value: formatNumberValue(raw, sequence.padding, sequence.prefix, sequence.suffix), raw, index, number, letter };
}

export function renderSequenceTemplate(template: string, item: SequenceValue): string {
  return replaceSequenceTokens(template || '{value}', item);
}

export function sequenceItems(state: AppState): SequenceValue[] {
  return Array.from({ length: Math.max(1, Math.min(500, Math.round(state.sequence.count))) }, (_, index) =>
    formatSequenceItem(state.sequence, index),
  );
}

export function sequenceValues(state: AppState): string[] {
  return sequenceItems(state).map((item) => item.value);
}

function payloadForSequence(mode: BarcodeMode, item: SequenceValue, lines: string[], template: string): string {
  if (mode === 'value') return item.value;
  if (mode === 'first_line') return lines.find((line) => line.trim()) ?? item.value;
  if (mode === 'all_text') return lines.filter((line) => line.trim()).join(' | ') || item.value;
  if (mode === 'template') return renderSequenceTemplate(template || '{value}', item);
  return '';
}

export function buildSpec(state: AppState, item: SequenceValue = sequenceItems(state)[0]): LabelSpec {
  const mode = state.mode;
  const sequenceActive = mode === 'sequence' || mode === 'sequence_code';
  const codeActive = mode === 'text_code' || mode === 'code' || mode === 'sequence_code';
  let text = state.text;
  if (mode === 'code') text = '';
  if (sequenceActive) text = renderSequenceTemplate(state.sequence.template, item);
  const lines = cleanLines(text);
  let barcodeText = codeActive ? state.codeContent : '';
  if (mode === 'sequence_code') {
    barcodeText = payloadForSequence(state.sequence.barcodeMode, item, lines, state.sequence.barcodeTemplate);
  }
  return {
    lines,
    widthMm: state.widthMm,
    heightMm: state.heightMm,
    dpi: state.dpi,
    copies: state.copies,
    border: state.border,
    inverted: state.inverted,
    fontSize: state.fontSize,
    alignment: state.alignment,
    autoFit: state.autoFit,
    lineGap: state.lineGap,
    barcode: Boolean(codeActive && barcodeText.trim()),
    barcodeType: state.codeType,
    barcodeText,
    barcodePosition: state.codePosition,
    barcodeArea: state.codeArea,
    barcodeMagnification: state.codeMagnification,
    showBarcodeText: state.showBarcodeText,
  };
}

export function generateOutputZpl(state: AppState): string {
  if (state.mode === 'sequence' || state.mode === 'sequence_code') {
    return sequenceItems(state)
      .map((item) => generateZpl(buildSpec(state, item)))
      .join('\n');
  }
  if (state.mode === 'batch') {
    return state.batchText
      .split(/\n\s*\n/g)
      .map((block) => block.trim())
      .filter(Boolean)
      .map((block) => generateZpl({ ...buildSpec({ ...state, mode: 'text' }), lines: cleanLines(block) }))
      .join('\n');
  }
  return generateZpl(buildSpec(state));
}
