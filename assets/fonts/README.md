# Interface fonts

The UI bundles its fonts because browsers cannot reach system fonts, and missing glyphs made desktop builds load large system fallback fonts.

- `Inter.ttf`: body text, buttons and labels. Variable font (`opsz`, `wght`), used at its default Regular instance. Copyright 2020 The Inter Project Authors, [rsms/inter](https://github.com/rsms/inter). Licence: `Inter-OFL.txt`.
- `Gelasio.ttf`: serif headings, designed to match Georgia's proportions. Variable font (`wght`), used at Regular. Copyright 2022 The Gelasio Project Authors, [SorkinType/Gelasio](https://github.com/SorkinType/Gelasio). Licence: `Gelasio-OFL.txt`. It has no check mark (✓), so Inter is set as its fallback.

Both files were downloaded on 23 September 2026 from [google/fonts](https://github.com/google/fonts) (`ofl/inter/Inter[opsz,wght].ttf`, `ofl/gelasio/Gelasio[wght].ttf`) and are used under the SIL Open Font License 1.1. The licence texts ship in every export through the presets' include filter.
