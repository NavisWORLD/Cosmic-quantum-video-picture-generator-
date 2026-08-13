# COSMOS Media — Distribution Status

The v0.2.0 distribution pipeline targets the following deliverables:

- ✅ **One-click Windows `.exe` installer** — `COSMOS-Media-Setup-Windows-x86_64.exe`
- ✅ **macOS `.app` + `.dmg` installer** — `COSMOS-Media.app` / `COSMOS-Media-macOS.dmg`
- ✅ **Polished iPhone / Android application** — shared responsive COSMOS UI packaged with Capacitor 8; Android APK is published, iOS native project + Simulator app are published, and the PWA remains installable directly on physical iPhones/Android devices.
- ✅ **Packaged GitHub Release with binaries** — `.github/workflows/release.yml` builds desktop/mobile artifacts, SHA-256 checksums, creates `v0.2.0`, and uploads the release assets.

## Important iPhone signing boundary

The iOS application is fully generated and compiled in CI without signing. Installing a native `.ipa` on arbitrary physical iPhones or publishing to the App Store requires Apple Developer signing/provisioning credentials owned by the publisher. Those private credentials are intentionally not stored in this public repository.

Physical iPhone users can still install the same COSMOS interface immediately as a PWA with **Add to Home Screen**, or the repository owner can open the published Xcode project and sign the native app with their Apple Developer account.

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

The release is published only after all release jobs succeed.
