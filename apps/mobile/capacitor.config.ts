import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'world.navis.cosmosmedia',
  appName: 'COSMOS Media',
  webDir: '../pwa',
  server: {
    cleartext: true
  },
  android: {
    allowMixedContent: true
  }
};

export default config;
