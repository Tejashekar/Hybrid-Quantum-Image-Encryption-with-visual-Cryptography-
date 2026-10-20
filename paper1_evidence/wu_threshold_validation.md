# Wu critical-value formula check

Computed using the implementation in `collect_controlled.py`; NPCR uses the one-sided 5% normal quantile and UACI uses the two-sided 95% interval.

- N=65,536: NPCR 99.5693% (expected 99.5693%); UACI [33.2824, 33.6447]% (expected [33.2824, 33.6447]).
- N=16,384: NPCR 99.5292% (expected 99.5292%); UACI [33.1012, 33.8259]% (expected [33.1012, 33.8259]).
