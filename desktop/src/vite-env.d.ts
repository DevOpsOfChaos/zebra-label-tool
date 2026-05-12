/// <reference types="vite/client" />

declare module '@tauri-apps/api/core' {
  export function invoke<T = unknown>(cmd: string, args?: Record<string, unknown>): Promise<T>;
}

declare module 'bwip-js' {
  const bwipjs: {
    toCanvas(canvas: HTMLCanvasElement, options: Record<string, unknown>): void;
  };
  export default bwipjs;
}
