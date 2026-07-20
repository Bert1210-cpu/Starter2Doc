# V0.18 Known Issues

- Upper 16-bit source parameter decoding is treated as proven by current reference projects.
- Lower 16-bit selector is classified structurally, but object/index/bit semantics remain unproven.
- Cross-object graph edges use a selector placeholder until object mapping is derived.
- `r1` is classified separately, but its exact STARTER semantic still requires validation.
- BICO paths are marked PARTIAL whenever selector/object semantics are unresolved.
