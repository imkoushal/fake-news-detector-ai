import { useEffect } from 'react';
import { Capacitor } from '@capacitor/core';

/**
 * Initializes native platform features when running inside Capacitor.
 * - Sets dark status bar style
 * - Handles Android hardware back button
 * - Provides haptic feedback utilities
 *
 * This hook is a no-op on web — safe to call unconditionally.
 */
export function useNativeApp() {
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;

    let cleanup: (() => void) | undefined;

    const init = async () => {
      // Status Bar — dark overlay style matching our dark theme
      try {
        const { StatusBar, Style } = await import('@capacitor/status-bar');
        await StatusBar.setStyle({ style: Style.Dark });
        await StatusBar.setBackgroundColor({ color: '#0a0a0f' });
      } catch {
        // StatusBar plugin may not be available — silently ignore
      }

      // Hardware back button — navigate back or minimize
      try {
        const { App: CapApp } = await import('@capacitor/app');
        const listener = await CapApp.addListener('backButton', ({ canGoBack }) => {
          if (canGoBack) {
            window.history.back();
          } else {
            CapApp.minimizeApp();
          }
        });
        cleanup = () => { listener.remove(); };
      } catch {
        // App plugin may not be available — silently ignore
      }
    };

    init();

    return () => { cleanup?.(); };
  }, []);
}

/**
 * Fire a short haptic feedback (impact light).
 * No-op on web.
 */
export async function hapticTap() {
  if (!Capacitor.isNativePlatform()) return;
  try {
    const { Haptics, ImpactStyle } = await import('@capacitor/haptics');
    await Haptics.impact({ style: ImpactStyle.Light });
  } catch {
    // Haptics plugin may not be available
  }
}
