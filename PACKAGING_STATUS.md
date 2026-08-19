# COSMOS Media — Distribution Status

The v0.3.0 distribution pipeline targets the following deliverables:

- ✅ **One-click Windows `.exe` installer** — `COSMOS-Media-Setup-Windows-x86_64.exe`
- ✅ **macOS `.app` + `.dmg` installer** — `COSMOS-Media.app` / `COSMOS-Media-macOS.dmg`
- ✅ **Polished iPhone / Android application** — the shared responsive COSMOS UI is packaged with Capacitor 8 and now includes upload + prompt editing, model switching, result preview and sharing.
- ✅ **Linux desktop/CLI bundle** — `COSMOS-Media-Linux-x86_64.tar.gz`
- ✅ **Packaged GitHub Release with binaries** — `.github/workflows/release.yml` builds desktop/mobile artifacts, SHA-256 checksums, creates `v0.3.0`, and uploads the release assets after merge to `main`.

## v0.3.0 application features

The packaged UI contains the same feature set on desktop, PWA, Android and iOS shells:

- native image generation;
- long-form native video generation;
- storybooks and branch planning;
- **Edit Uploaded Image**;
- **Edit Uploaded Video**;
- default **COSMOS Main** model identity with switchable edit renderer;
- Synaptic edit continuity and hashed edit receipts;
- configurable Engine URL for mobile/LAN/remote use.

`phera-ra/QC67_cosmo` is the COSMOS Main controller identity. Because the published QC67 model task is text generation, the visual renderer that actually modifies pixels/video is tracked separately (`native` or configured `http` editor).

## Important iPhone signing boundary

The iOS application is generated and compiled in CI without private signing credentials. Installing a native `.ipa` on arbitrary physical iPhones or publishing to the App Store requires Apple Developer signing/provisioning credentials owned by the publisher. Those credentials are intentionally not stored in this repository.

Physical iPhone users can still install the same COSMOS interface as a PWA with **Add to Home Screen**, or the repository owner can open the published Xcode project and sign the native app with their Apple Developer account.

## Release asset set

```text
COSMOS-Media-Setup-Windows-x86_64.exe
COSMOS-Media-CLI-Windows-x86_64.exe
COSMOS-Media-macOS.dmg
COSMOS-Media-macOS.app.zip
COSMOS-Media-CLI-macOS
COSMOS-Media-Linux-x86_64.tar.gz
COSMOS-Media-Android.apk
COSMOS-Media-iOS-Simulator.app.zip
COSMOS-Media-iOS-Xcode-Project.zip
SHA256SUMS.txt
```

## Build verification

Pull requests touching packaging run `.github/workflows/package-ci.yml`, which independently builds:

1. Windows installer on `windows-latest`;
2. macOS app/DMG on `macos-latest`;
3. Android APK on Ubuntu with Java 21 + Capacitor 8.4.2;
4. iOS Simulator app/native project on `macos-latest`.

The Python CI additionally creates a real generated image/video, edits both with the new CLI paths, verifies the outputs, checks that `cosmos-main` is the default model identity, and uploads proof artifacts.

The GitHub Release is published only after all release build jobs succeed.
