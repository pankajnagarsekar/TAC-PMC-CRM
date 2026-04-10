/* global jest */
// Jest setup for React Native / Expo
// Sets up gesture handler and reanimated mocks

require('react-native-gesture-handler/jestSetup');

// Reanimated v4 built-in mock
jest.mock('react-native-reanimated', () =>
  require('react-native-reanimated/mock')
);

// Expo 54 winter runtime import.meta workaround
// The expo/src/winter/installGlobal registers __ExpoImportMetaRegistry which
// tries to import a file outside the test scope. Mock it out.
jest.mock('expo/src/winter/runtime.native', () => ({}), { virtual: true });
