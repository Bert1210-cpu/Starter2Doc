# Starter2Doc 0.20.0

Starter2Doc converts Siemens STARTER project ZIP exports into clean engineering documentation.

## Primary output

```bash
python -m starter2doc Project.zip -o Project_Documentation.docx
```

The default output is now a DOCX. Internal parser and analysis information stays out of the customer document.

Optional switches:

```bash
--include-unused   Add unused DCC blocks as a compact appendix
--debug            Also write the engineering JSON/TXT reports
```

## 0.20.0 architecture

```text
STARTER ZIP
  -> EngineeringModel
  -> DocumentModelBuilder
  -> DocumentModel
  -> WordExporter
```

`DocumentModel` contains presentation-neutral sections, paragraphs and tables. Word-specific formatting exists only in `WordExporter`.

The current Word output contains only information already proven by the parsers: project overview, PZD communication, used DCC blocks, parameter symbols and optional appendices. Hardware and motor chapters will be added when those data are available in the EngineeringModel; empty or invented chapters are not generated.
