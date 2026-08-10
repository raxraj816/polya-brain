# Deterministic Simulation and Controlled Experiment Capabilities

Status: implemented as bounded MVP execution capabilities.

## Scenario Simulation

The `simulator` executes exact Decimal compound-growth sensitivity models over
an explicit typed specification:

- baseline value;
- bounded period count;
- named per-period rates;
- optional threshold;
- unit.

It returns every trajectory and first threshold-crossing period. A specification
can come from an explicit `SIMULATION_SPEC`, an assigned plan task, or a
schema-bound model translation only when that model is approved for the data.
Missing numbers cause a human-input pause; they are never invented.

## Controlled Experiment Evaluation

The `experiment` capability evaluates explicit numeric control and treatment
observations. It requires the supplied design to assert randomization and
independent observations, then reports:

- sample counts and means;
- absolute and relative effect;
- standard error;
- approximate 95% normal interval;
- direction and minimum-effect checks;
- whether the interval excludes zero in the desired direction.

The result explicitly records that the interval is an approximation and that
PolyaBrain did not independently observe randomization or independence. This is
an offline evaluation tool; it does not autonomously intervene in real systems
or enroll human subjects.

Both capabilities produce evidence, trace events, and plan execution artifacts.
Direct gap actions resolve only when a validated explicit spec is executed.
