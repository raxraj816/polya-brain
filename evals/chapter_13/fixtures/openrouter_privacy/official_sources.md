# OpenRouter data-policy sources

- OpenRouter provider routing documents `provider.data_collection` with values
  `allow` or `deny`; `deny` restricts routing to providers that do not collect
  user data. Source: https://openrouter.ai/docs/guides/routing/provider-selection
- The configured NVIDIA Nemotron 3 Ultra free endpoint warns users not to send
  confidential or personal data and states that session data is logged for
  security and model improvement. Source:
  https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b%3Afree/api
- OpenRouter documents strict parameter routing through
  `provider.require_parameters=true`. Source:
  https://openrouter.ai/docs/guides/features/structured-outputs

These are paraphrased source notes captured for a reproducible technical
investigation. The live probe result is stored separately.
