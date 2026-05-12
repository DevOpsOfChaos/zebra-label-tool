import type { Alignment, AppState, BarcodeMode, BarcodeType, CodePosition } from './domain';

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
  const margin = 20;
  const gap = 14;
  const codeActive = spec.barcode && spec.barcodeText.trim().length > 0;
  const barH = codeHeight(spec);
  let textX = margin;
  let textY = 4;
  let textW = Math.max(1, pw - margin * 2);
  let barX = margin;
  let barY = 4;

  const lineCount = Math.max(1, spec.lines.length);
  let fs = Math.max(8, Math.round(spec.fontSize));
  if (spec.autoFit) {
    const longest = Math.max(...spec.lines.map((line) => line.length), 1);
    const maxChars = spec.barcodePosition === 'left' || spec.barcodePosition === 'right' ? 18 : 28;
    if (longest > maxChars) fs = Math.max(8, Math.floor((fs * maxChars) / longest));
  }
  const textH = fs * lineCount + Math.max(0, spec.lineGap) * Math.max(0, lineCount - 1);

  if (!codeActive) {
    textY = Math.max(4, Math.round((ll - textH) / 2));
  } else if (spec.barcodePosition === 'right') {
    const codeW = Math.min(Math.max(barH, Math.round(spec.barcodeArea)), Math.max(40, pw - margin * 3));
    textW = Math.max(1, pw - margin * 3 - codeW - gap);
    textX = margin;
    textY = Math.max(4, Math.round((ll - textH) / 2));
    barX = margin + textW + gap;
    barY = Math.max(2, Math.round((ll - barH) / 2));
  } else if (spec.barcodePosition === 'left') {
    const codeW = Math.min(Math.max(barH, Math.round(spec.barcodeArea)), Math.max(40, pw - margin * 3));
    barX = margin;
    barY = Math.max(2, Math.round((ll - barH) / 2));
    textX = margin + codeW + gap;
    textW = Math.max(1, pw - textX - margin);
    textY = Math.max(4, Math.round((ll - textH) / 2));
  } else if (spec.barcodePosition === 'above') {
    barX = margin;
    barY = 4;
    textY = Math.max(barY + barH + gap, Math.round((ll - textH) / 2));
  } else {
    textY = Math.max(4, Math.round((ll - barH - gap - textH) / 2));
    barX = margin;
    barY = Math.min(Math.max(2, textY + textH + gap), Math.max(2, ll - barH - 4));
  }

  return { pw, ll, margin, fs, textX, textY, textW, barX, barY, barH };
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

export function buildSpec(state: AppState, sequenceValue?: string, rawNumber = state.sequence.start, sequenceIndex = 0): LabelSpec {
  const mode = state.mode;
  const sequenceActive = mode === 'sequence' || mode === 'sequence_code';
  const codeActive = mode === 'text_code' || mode === 'code' || mode === 'sequence_code';
  let text = state.text;
  if (mode === 'code') text = state.caption;
  if (sequenceActive) {
    text = renderSequenceTemplate(state.sequence.template, sequenceValue ?? formatSequenceValue(rawNumber, state.sequence.padding, state.sequence.prefix, state.sequence.suffix), rawNumber, sequenceIndex);
  }
  const lines = cleanLines(text);
  let barcodeText = codeActive ? state.codeContent : '';
  if (mode === 'sequence_code') {
    barcodeText = payloadForSequence(state.sequence.barcodeMode, sequenceValue ?? '', lines);
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

export function formatSequenceValue(raw: number, padding: number, prefix: string, suffix: string): string {
  const sign = raw < 0 ? '-' : '';
  return `${prefix}${sign}${Math.abs(Math.round(raw)).toString().padStart(Math.max(0, padding), '0')}${suffix}`;
}

export function renderSequenceTemplate(template: string, value: string, raw: number, index: number): string {
  return String(template || '{value}')
    .replaceAll('{value}', value)
    .replaceAll('{number}', value)
    .replaceAll('{raw}', String(raw))
    .replaceAll('{index}', String(index + 1))
    .replaceAll('{index0}', String(index));
}

export function sequenceValues(state: AppState): string[] {
  return Array.from({ length: Math.max(1, Math.min(500, Math.round(state.sequence.count))) }, (_, index) => {
    const raw = state.sequence.start + index * state.sequence.step;
    return formatSequenceValue(raw, state.sequence.padding, state.sequence.prefix, state.sequence.suffix);
  });
}

function payloadForSequence(mode: BarcodeMode, value: string, lines: string[]): string {
  if (mode === 'value') return value;
  if (mode === 'first_line') return lines.find((line) => line.trim()) ?? value;
  if (mode === 'all_text') return lines.filter((line) => line.trim()).join(' | ') || value;
  return '';
}

export function generateOutputZpl(state: AppState): string {
  if (state.mode === 'sequence' || state.mode === 'sequence_code') {
    return sequenceValues(state)
      .map((value, index) => {
        const raw = state.sequence.start + index * state.sequence.step;
        return generateZpl(buildSpec(state, value, raw, index));
      })
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
