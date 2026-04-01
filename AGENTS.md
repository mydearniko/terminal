# Project Guidelines

## What This Is

This is a **personal fork** of [microsoft/terminal](https://github.com/microsoft/terminal) (Windows Terminal).
The upstream repo is at `https://github.com/microsoft/terminal`. My fork is at `https://github.com/mydearniko/terminal`.

The single purpose of this fork is to add **country flag emoji support** to Windows Terminal. Windows doesn't render country flag emoji (like 🇺🇸 🇩🇪 🇯🇵) because Segoe UI Emoji doesn't include flag ligatures. This fork patches the DirectWrite font fallback chain to route flag codepoints to a Twemoji-based font instead.

## The Patch

There is exactly **one source code change** — in `src/renderer/atlas/AtlasEngine.api.cpp` inside `_resolveFontMetrics()` (around line 721).

It adds a ~48-line block that:
1. Searches for an installed Twemoji font (tries "Twemoji Mozilla", "Twemoji", "Twitter Color Emoji", "Noto Color Emoji" in order)
2. Creates a `IDWriteFontFallbackBuilder` mapping for three Unicode ranges:
   - `U+1F1E6–1F1FF` — Regional Indicator Symbols (letter pairs that form country flags)
   - `U+1F3F4` — Waving Black Flag (used in subdivision flag sequences like 🏴󠁧󠁢󠁥󠁮󠁧󠁿)
   - `U+E0061–E007F` — Tags Block (region subtag letters + cancel tag)
3. Inserts this mapping **before** the system fallback so it takes priority over Segoe UI Emoji

The user must install a Twemoji font (e.g. "Twemoji Mozilla") on their Windows system for flags to render.

## Build System

- **Solution**: `OpenConsole.slnx` (MSBuild, C++/WinRT, UWP/MSIX packaging)
- **CI**: `.github/workflows/build.yml` — GitHub Actions on `windows-2022` runner
- **Output**: MSIX installer at `src/cascadia/CascadiaPackage/AppPackages/`
- **Signing**: Self-signed cert (Subject: `CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US`, password: `BuildCert123!`). Sideloading requires trusting the exported `.cer` file.
- **Branding**: Builds as "Windows Terminal (Dev)" so it doesn't conflict with the store version

### Build commands (CI)

```powershell
# NuGet restore
nuget restore build/packages.config -ConfigFile NuGet.config -PackagesDirectory packages
msbuild OpenConsole.slnx /t:Restore /p:Platform=x64 /p:Configuration=Release /m
nuget restore dep/nuget/packages.config -ConfigFile NuGet.config -PackagesDirectory packages

# Build
msbuild OpenConsole.slnx /p:Configuration=Release /p:Platform=x64 /p:WindowsTerminalOfficialBuild=true /p:WindowsTerminalBranding=Dev /p:PGOBuildMode=None /p:PackageCertificatePassword=BuildCert123! /t:Terminal\CascadiaPackage /m
```

### CI Caching

The workflow caches three things to make rebuilds fast (~5 min instead of ~20 min):
- **NuGet packages** (`packages/`) — keyed on packages.config hashes
- **vcpkg** (`dep/vcpkg/` + `obj/x64/vcpkg/`) — keyed on baseline commit + vcpkg.json
- **Compiled objects** (`obj/`) — keyed on commit SHA with prefix restore for incremental builds

vcpkg baseline commit: `15e5f3820f0370f1ba7150853762cec0688cd396`

## Syncing with Upstream

When syncing my fork with the latest upstream microsoft/terminal:
1. The only file I've changed is `src/renderer/atlas/AtlasEngine.api.cpp` (the flag fallback block ~line 721)
2. The CI workflow `.github/workflows/build.yml` is new (doesn't exist upstream)
3. Merge conflicts are only likely in `AtlasEngine.api.cpp` — resolve by keeping my flag fallback block in its position inside `_resolveFontMetrics()`, right after the `primaryFontFamily` lookup and before the `fontFallback` assignment

## Architecture Context

The rendering pipeline: Terminal → `AtlasEngine` (Direct2D/Direct3D) → DirectWrite for text shaping → font fallback chain for glyph resolution. My patch hooks into the font fallback chain creation step.

Key files:
- `src/renderer/atlas/AtlasEngine.api.cpp` — **patched** — font metric resolution and fallback
- `src/renderer/atlas/AtlasEngine.cpp` — main rendering engine
- `src/renderer/atlas/AtlasEngine.r.cpp` — rendering pass
- `src/cascadia/CascadiaPackage/` — MSIX packaging project

## Conventions

- Keep the patch minimal — only the flag fallback block, nothing else
- Don't modify upstream code beyond what's needed for flags
- The CI workflow is the only other addition; keep it self-contained
- When I say "flags" or "flag emoji" I mean country/region flag emoji (🇺🇸 🇬🇧 🏴󠁧󠁢󠁳󠁣󠁴󠁿 etc.)
- When I say "the patch" I mean the flag fallback block in AtlasEngine.api.cpp
- When I say "build" or "rebuild" I mean triggering the GitHub Actions workflow
