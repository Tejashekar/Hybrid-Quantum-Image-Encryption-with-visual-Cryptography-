# Phase 6 v2 rerun comparison

**Status: BLOCKED; no rerun or comparison was performed.** At the start of evidence collection, `QCRYPT_EXPERIMENT_KEY_HEX` was unset and the configured fallback file was not available. Those checks tested only presence and did not read either value. The repository loader requires a caller-provided experiment key (`experiments/key_material.py:11-27`), and the v2 runner loads it when no explicit key is supplied (`experiments/phase6_security.py:276-282`).

Required to resume: make the original experiment key available through the configured `QCRYPT_EXPERIMENT_KEY_HEX` environment variable. The key itself must not be pasted into a chat, report, command output, or evidence file. No replacement key was generated.

The runner's current documented configuration list includes A-D **and** four E threshold configurations (`experiments/phase6_security.py:56-58`), whereas the Paper 1 task wording says A-D. This protocol discrepancy must be resolved before claiming an exact A-D-only rerun. The runner also refuses an existing output directory and defaults to the archived v2 path; neither was invoked (`experiments/phase6_security.py:50,276-281`).

No CSV comparisons were possible; no mismatch is claimed. `rerun_v2/` contains only a status note, no generated run outputs.
