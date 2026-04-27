// Prevent expo/src/winter/runtime.native.ts from overriding globals with lazy getters
// that require ESM-only modules (@ungap/structured-clone, ImportMetaRegistry).
// Strategy: define properties as configurable:false so installGlobal() skips them.

const defineNonConfigurable = (name, value) => {
  try {
    const existing = Object.getOwnPropertyDescriptor(global, name);
    // Only override if configurable (i.e., not yet locked)
    if (!existing || existing.configurable) {
      Object.defineProperty(global, name, {
        value,
        configurable: false,
        writable: true,
        enumerable: true,
      });
    }
  } catch {
    // ignore — some globals can't be redefined
  }
};

// Prevent structuredClone lazy getter (would load @ungap/structured-clone via ESM)
// Node.js 17+ has native structuredClone; provide a polyfill for older envs
if (typeof global.structuredClone !== 'function') {
  defineNonConfigurable('structuredClone', (obj) => JSON.parse(JSON.stringify(obj)));
} else {
  defineNonConfigurable('structuredClone', global.structuredClone);
}

// Prevent __ExpoImportMetaRegistry lazy getter
defineNonConfigurable('__ExpoImportMetaRegistry', { url: null });

// Prevent TextDecoder/TextEncoder lazy getters (they may also be ESM)
if (typeof global.TextDecoder !== 'undefined') {
  defineNonConfigurable('TextDecoder', global.TextDecoder);
}
if (typeof global.TextEncoder !== 'undefined') {
  defineNonConfigurable('TextEncoder', global.TextEncoder);
}
