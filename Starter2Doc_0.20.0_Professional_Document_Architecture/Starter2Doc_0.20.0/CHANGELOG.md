# Changelog

## 0.20.0 - Professional Document Architecture

- Added a presentation-neutral `DocumentModel`.
- Added `DocumentModelBuilder` to define document content and chapter order.
- Added a clean DOCX `WordExporter` with cover page, headings and consistent tables.
- Word is now the default primary output.
- Internal diagnostics stay outside the customer document unless explicitly requested.
- Used DCC blocks appear in the main document; unused blocks are optional in the appendix.
- Added CLI switches `--include-unused` and `--debug`.
- No invented hardware or motor chapters: only parser-proven data is documented.
