## p · r.example/a:1

`sha256:1111111111111111111111111111111111111111111111111111111111111111`

```mermaid
%%{init: {"theme": "default", "themeVariables": {"cScale0": "#002d51", "cScaleLabel0": "#ffffff", "cScale1": "#c80e0e", "cScaleLabel1": "#ffffff"}}}%%
timeline
    title r.example/a#58;1
    section 2026-10-01 00#58;00
        placed-by-exception : r#58;1 #35;2#59; 3#37;#37; 4|5 6
    section 2026-10-01 00#58;00
        quarantine : —
```

| ts | run | state | reason | ruleset | report | details |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-01T00:00:00Z |  | placed-by-exception | r:1 #2; 3%% 4\|5 6 | none |  | arbitration: {"by": "b", "reason": "x\|y\r\nz"} |
| 2026-10-01T00:00:00Z |  | quarantine | — |  |  |  |