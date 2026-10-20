# Q-CRYPT manuscript cleanup report

Date: 2026-10-14 (Asia/Calcutta)

## Files changed

- Updated `main.tex` with a cleaned IEEEtran conference manuscript.
- Created `main.before-cleanup.tex.bak`, an unchanged backup of the populated manuscript before edits.
- Updated this report.
- The earlier `main.tex.bak` remains untouched; it is the zero-byte backup made when `main.tex` was empty.

No unrelated project files, experiment archives, or existing working-tree changes were modified.

## Manuscript changes

- Removed literal Markdown fences, the malformed sample table, generic IEEE template instructions, placeholder/example figure, generic acknowledgment/references instructions, fake example bibliography, and red template warning.
- Kept all six author names and email addresses in the requested reading order with IEEE conference author blocks.
- Kept and corrected five Q-CRYPT tables: configuration definitions (I), notation (II), dataset/preprocessing (III), archived experimental results and limitations (IV), and functional verification evidence (V).
- Kept the conceptual TikZ architecture figure, updated its caption to match the documented classical workflow, and added an in-text reference.
- Replaced placeholder title, abstract, keywords, and generic body with a cautious account of the project. Related work, complete algorithm details, and acknowledgment are explicitly marked TODO because verified source material is absent. No bibliography entries were fabricated.
- Table III now states that seven files represent five unique decoded contents, and identifies the preprocessing and recovery boundary.
- Table IV uses only Phase 6 v2 archive figures and labels their scope and provenance limitations. It reports five unique contents, five timing repetitions per image/configuration, entropy and correlation ranges, controlled NPCR/UACI measurements, the narrow diffusion property, runtime means, and archived threshold outcomes. It marks peak memory as not implemented and published comparison as not run/not verifiable.
- Table V reports the focused local audit separately: 113 tests passed in 15.76 seconds. It does not claim the full 263-test suite passed. Qiskit and frontend checks are marked not run/not verifiable.
- The manuscript explicitly avoids claims of post-quantum security, quantum advantage, formal security proof, or effective 256-bit security. It discloses that the v2 archive lacks source-version binding and original timing-environment metadata.

## Evidence reviewed

- `docs/research/TABLE_IV_V_EVIDENCE_AUDIT.md`
- `docs/research/TABLE_IV_V_REVISION_NOTES.md`
- Project `README.md`

The two evidence notes report the archive and local test details summarized above. The 113-test local run is not represented as an archived Phase 6 measurement. The archive’s 25 timing observations per configuration come from five images repeated five times; they are not 25 independent images. The archived key is absent, and v1/v1.1 were not used as substitutes for v2.

## Compilation and PDF inspection

Compilation could not be attempted because this environment has no available `pdflatex`, `xelatex`, `lualatex`, `latexmk`, or `tectonic` command. No PDF was generated or inspected. As a result, final two-column pagination, rendered author-block row arrangement, overfull boxes, and PDF appearance remain unverified.

## Unresolved TODOs and limitations

1. Add verified related-work sources and citations; the project does not supply citable references.
2. Complete the algorithm and threat-model description from authoritative source material; do not infer missing construction details.
3. Obtain funding/contributor information before replacing the acknowledgment TODO.
4. Resolve v2 source-version and timing-environment provenance before presenting timing as reproducible or attributable to the current checkout.
5. Capture logs before claiming the full 263-test suite, Qiskit validation, or frontend checks passed.
6. Compile with IEEEtran and inspect the PDF when an engine is available; adjust any layout issues identified there.

This is a cleaned, evidence-bounded manuscript draft, not a fully validated or submission-ready paper.
