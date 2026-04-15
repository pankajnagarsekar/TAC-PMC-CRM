module.exports = {
  preset: 'jest-expo',
  testRegex: '/__tests__/.*\\.test\\.(ts|tsx)$',
  // Run expo global patch before any test module is loaded (before jest-expo's own setupFiles)
  setupFiles: [
    require.resolve('./jest-shims/expo-global-setup.js'),
  ],
  setupFilesAfterEnv: [
    require.resolve('./jest.setup.js'),
  ],
  transformIgnorePatterns: [
    '/node_modules/(?!(.pnpm|react-native|@react-native|@react-native-community|expo|@expo|@expo-google-fonts|react-navigation|@react-navigation|@shopify/flash-list|react-native-svg|react-native-gesture-handler|react-native-reanimated|react-native-worklets))',
    '/node_modules/react-native-reanimated/plugin/',
  ],
};
