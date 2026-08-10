# Data Analysis

## Define the baseline

Every claim of change needs a reference condition with the same metric definition, population, and time granularity. Record the baseline window before calculating a difference. Compare absolute and relative change, because either alone can mislead when the baseline is very small or very large.

## Inspect data quality and distributions

Count rows, missing values, duplicates, invalid types, and impossible ranges before modeling. Summaries should include distribution shape and robust statistics, not only the mean. Preserve provenance for the dataset and every transformation used to produce the result.

## Segment before generalizing

Aggregate movement can hide opposing group behavior. Compare meaningful segments with adequate sample size and consistent definitions. Treat a discovered segment difference as a hypothesis until it survives multiple-comparison, selection, and measurement-bias checks.

## Separate association from causality

An observational comparison can identify association but usually cannot establish intervention effect. For causal questions, prefer a randomized controlled experiment when safe and feasible; otherwise state assumptions, confounders, uncertainty, and alternative explanations explicitly.
