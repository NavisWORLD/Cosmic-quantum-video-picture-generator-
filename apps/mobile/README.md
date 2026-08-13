# COSMOS Media Mobile

This directory packages the same COSMOS PWA interface as a native iPhone/Android application using Capacitor.

The mobile shell is a client for a running COSMOS engine. Set **Engine URL** in the app to one of:

- `http://192.168.x.x:8788` for a COSMOS engine on your local network;
- an HTTPS COSMOS deployment you control;
- the desktop machine running `COSMOS-Media` / `cosmos-media serve`.

The PWA remains installable directly from Safari/Chrome as well.

## Android

```bash
cd apps/mobile
npm install
npx cap add android
npx cap sync android
cd android
./gradlew assembleDebug
```

The GitHub release workflow builds and publishes an installable debug APK named `COSMOS-Media-Android.apk`. A Play Store AAB can be produced with your signing key for store distribution.

## iPhone / iOS

```bash
cd apps/mobile
npm install
npx cap add ios
npx cap sync ios
npx cap open ios
```

The GitHub release workflow compiles a no-sign iOS Simulator `.app` and publishes the generated native iOS project as an artifact. Installation on physical iPhones/App Store distribution requires Apple code-signing credentials and provisioning controlled by the repository owner; those secrets are intentionally not committed.

For a physical iPhone without Apple signing, the PWA remains directly installable using **Add to Home Screen** and uses the same mobile UI.

## Architecture

```text
iPhone / Android app
        |
        | HTTP(S)
        v
COSMOS Media Engine
  - native renderer
  - CST state / Hebbian continuity
  - branch planner
  - image/video/storybook jobs
  - long-form checkpoints
  - quantum provenance (optional)
```

The mobile shell does not duplicate the Python media engine inside a phone WebView. This keeps the engine singular and lets mobile clients connect to a workstation, render server, or hosted COSMOS instance.
