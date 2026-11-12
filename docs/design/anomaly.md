## IsolationForest comparison decision - 11 November 2026

The exploratory comparison in [Anomaly Findings](anomaly_findings.md) evaluated IsolationForest and the rolling z-score detector using four synthetic fixtures.

Unlike the initial experiment, each IsolationForest model was fitted on the first five prices of one product and scored on that product's latest price. Four random states were evaluated.

The rolling z-score detector correctly classified all four fixtures. IsolationForest missed the significant price drop in every run, while its predictions for the other cases varied across random states. Each model had only five baseline observations, making its predictions unstable for this experiment.

**Decision: Keep the rolling z-score detector.** The experiment does not provide sufficient evidence to replace the production detector with IsolationForest. More independent data containing genuine price changes would be needed for further evaluation.

The production detector remains unchanged.

See [Anomaly Findings](anomaly_findings.md) for the complete configuration, results, and limitations.
