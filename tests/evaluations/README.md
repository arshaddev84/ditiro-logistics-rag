# RAG Evaluation Cases

`rag_cases.json` is a small, version-controlled evaluation set built only from the fictional documents in `docs/`. It records representative questions, expected source files, evidence that should support an answer, and whether the system should abstain from an unsupported conclusion.

These labels are a starting baseline for Phase 1. They are not results from a running model, do not measure answer accuracy, and do not establish customer or business value. Phase 2 should add a repeatable retrieval and answer evaluation runner, review expected evidence, and calibrate abstention behavior against representative cases.