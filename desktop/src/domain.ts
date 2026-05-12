export type Language = 'de' | 'en';
export type Theme = 'light' | 'dark';
export type WorkflowMode = 'text' | 'text_code' | 'code' | 'sequence' | 'sequence_code' | 'batch';
export type BarcodeType = 'code128' | 'code39' | 'ean13' | 'upca' | 'qrcode' | 'datamatrix' | 'pdf417';
export type CodePosition = 'below' | 'above' | 'right' | 'left' | 'center';
export type BarcodeMode = 'none' | 'value' | 'first_line' | 'all_text' | 'template';
export type Alignment = 'left' | 'center' | 'right';
export type SequenceKind = 'number' | 'letters' | 'mixed';

export interface SequenceState {
  kind: SequenceKind;
  start: number;
  letterStart: string;
  count: number;
  step: number;
  padding: number;
  prefix: string;
  suffix: string;
  template: string;
  barcodeMode: BarcodeMode;
  barcodeTemplate: string;
  valuePattern: string;
}

export interface AppState {
  language: Language;
  theme: Theme;
  sidebarCollapsed: boolean;
  mode: WorkflowMode;
  printer: string;
  printers: string[];
  widthMm: number;
  heightMm: number;
  dpi: number;
  copies: number;
  border: boolean;
  inverted: boolean;
  text: string;
  caption: string;
  fontSize: number;
  alignment: Alignment;
  autoFit: boolean;
  lineGap: number;
  codeEnabled: boolean;
  codeType: BarcodeType;
  codeContent: string;
  codePosition: CodePosition;
  codeArea: number;
  codeMagnification: number;
  showBarcodeText: boolean;
  sequence: SequenceState;
  batchText: string;
}

export const barcodeLabels: Record<BarcodeType, string> = {
  code128: 'Code 128',
  code39: 'Code 39',
  ean13: 'EAN-13',
  upca: 'UPC-A',
  qrcode: 'QR Code',
  datamatrix: 'Data Matrix',
  pdf417: 'PDF417',
};

export const modeOrder: WorkflowMode[] = ['text', 'text_code', 'code', 'sequence', 'sequence_code', 'batch'];
export const barcodeOrder: BarcodeType[] = ['code128', 'code39', 'ean13', 'upca', 'qrcode', 'datamatrix', 'pdf417'];
export const positionOrder: CodePosition[] = ['below', 'above', 'right', 'left', 'center'];
export const sequenceKindOrder: SequenceKind[] = ['number', 'letters', 'mixed'];
