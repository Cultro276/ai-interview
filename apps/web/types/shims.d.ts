/* Temporary type shims for browser env access if needed */
declare const process: { env?: { [key: string]: string | undefined } };

// Intentionally no React shims here to avoid clashing with @types/react

