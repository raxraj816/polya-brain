# Response-model defaults survive skip-default serialization

A route configured to skip response-model defaults still emits a field whose
value is the model default when the handler returns a model instance. Diagnose
where model semantics are lost and state the smallest correction and check.
