import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.verifai.app',
  appName: 'VerifAI',
  webDir: 'dist',
  server: {
    // Use https scheme so cookies and CORS work properly in the WebView
    androidScheme: 'https',
  },
  plugins: {
    StatusBar: {
      backgroundColor: '#0a0a0f',
      style: 'DARK',
    },
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: '#0a0a0f',
      androidScaleType: 'CENTER_CROP',
      showSpinner: false,
      launchShowDuration: 1500,
    },
  },
};

export default config;
