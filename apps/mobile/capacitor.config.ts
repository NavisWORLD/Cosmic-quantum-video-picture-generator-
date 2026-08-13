import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'world.navis.cosmosmedia',
  appName: 'COSMOS Media',
  webDir: '../pwa',
  server: {
    cleartext: true
  },
  android: {
    allowMixedContent: true,
    backgroundColor: '#090b17'
  },
  ios: {
    backgroundColor: '#090b17',
    contentInset: 'automatic'
  }
};

export default config;
