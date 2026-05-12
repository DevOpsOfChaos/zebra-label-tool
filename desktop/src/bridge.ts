import { invoke } from '@tauri-apps/api/core';

export async function listPrinters(): Promise<string[]> {
  try {
    const result = await invoke<string[]>('list_printers');
    return Array.isArray(result) ? result : [];
  } catch (error) {
    console.warn('Printer bridge unavailable', error);
    return [];
  }
}

export async function printZpl(printer: string, zpl: string): Promise<void> {
  await invoke('print_zpl', { printer, zpl });
}
