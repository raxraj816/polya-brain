"""Composition helpers for the first persisted cognitive session path."""

from __future__ import annotations

from collections.abc import Callable
from os import pathsep
from pathlib import Path

from app.acquisition import (
    AvailableDataSourceRegistry,
    BraveSearchProvider,
    DataSourceDefinition,
    DataSourceKind,
    LocalArtifactInspector,
    ResearchBudget,
    evidence_evaluator_capability,
    local_artifact_capability,
    web_search_capability,
)
from app.acquisition.openrouter import (
    SEARCH_OUTPUT_TOKEN_RESERVE,
    SEARCH_TIMEOUT_SECONDS,
    OpenRouterSearchProvider,
)
from app.acquisition.providers import SearchProvider
from app.cognition.adapters import (
    constraint_discovery_capability,
    problem_representation_capability,
)
from app.cognition.capabilities import CapabilityRegistry
from app.cognition.contracts import CapabilityKind
from app.cognition.controller import CognitiveController, ProceduralPreferenceProvider
from app.cognition.local_capabilities import calculator_capability, human_input_capability
from app.cognition.model_capabilities import planner_capability
from app.cognition.model_gateway import CognitiveModelGateway
from app.cognition.on_demand_capabilities import on_demand_cognitive_capabilities
from app.cognition.performance import CapabilityPerformanceLedger
from app.cognition.procedure_compiler import ProcedureCompiler
from app.cognition.runtime import CognitiveRuntime
from app.cognition.semantic_broker import (
    RoutedCognitiveModelGateway,
    RoutedProblemUnderstandingProvider,
    SemanticModelRoute,
    SemanticRouteHealthLedger,
)
from app.cognition.session_runner import CognitiveSessionRunner
from app.cognition.source_patch_investigation import source_patch_investigator_capability
from app.cognition.task_model import CognitiveResourceBudget
from app.config import Settings
from app.engines import ConstraintDiscoveryEngine, ProblemRepresentationEngine
from app.execution import (
    DockerPythonSandbox,
    DockerSandboxLimits,
    TableMeasurementTool,
    controlled_experiment_capability,
    python_sandbox_capability,
    scenario_simulation_capability,
    source_patch_sandbox_capability,
    table_measurement_capability,
)
from app.graph.state import StateEvent
from app.llm import FakeLLMClient, LLMClient, OpenRouterLLMClient
from app.memory.capability import SemanticMemorySearch, semantic_memory_capability
from app.models.contracts import EvidenceItem, ProductMode, RiskLevel


def build_cognitive_runtime(
    settings: Settings,
    *,
    enable_source_patch: bool = False,
    mode_hint: ProductMode | None = None,
    domain_hint: str | None = None,
    prior_research_query_count: Callable[[str], int] | None = None,
    semantic_memory: SemanticMemorySearch | None = None,
    procedural_memory: ProceduralPreferenceProvider | None = None,
    performance_ledger: CapabilityPerformanceLedger | None = None,
    semantic_route_health_ledger: SemanticRouteHealthLedger | None = None,
) -> CognitiveRuntime:
    """Compose the shared production runtime for API and local investigations.

    Deterministic fallbacks still work without credentials. Unrecognized inputs
    fail closed at the provider boundary instead of silently using the old stub.
    """
    adaptive_ledger = performance_ledger or CapabilityPerformanceLedger()
    configured_key = settings.openrouter_api_key.get_secret_value().strip()
    configured_model = settings.openrouter_model.strip()
    client: LLMClient
    if configured_key and configured_model:
        client = OpenRouterLLMClient.from_settings(settings)
        model = configured_model
    else:
        client = FakeLLMClient([])
        model = configured_model or "unconfigured-representation-provider"

    fallback_models = list(
        dict.fromkeys(
            item.strip()
            for item in settings.openrouter_fallback_models.split(",")
            if item.strip() and item.strip() != model
        )
    )
    if len(fallback_models) > 1:
        raise ValueError("the first semantic broker supports at most one fallback model")
    semantic_routes = [
        SemanticModelRoute(model_slug=model, priority=0, timeout_seconds=90.0),
        *[
            SemanticModelRoute(model_slug=fallback, priority=index, timeout_seconds=90.0)
            for index, fallback in enumerate(fallback_models, start=1)
        ],
    ]
    route_health = semantic_route_health_ledger or SemanticRouteHealthLedger()
    understanding_provider = (
        RoutedProblemUnderstandingProvider(
            client,
            semantic_routes,
            health_ledger=route_health,
        )
        if configured_key and configured_model
        else None
    )
    engine = ProblemRepresentationEngine(
        client=client,
        model=model,
        mode_hint=mode_hint,
        domain_hint=domain_hint,
        understanding_provider=understanding_provider,
    )
    gateway = (
        RoutedCognitiveModelGateway(
            client,
            semantic_routes,
            health_ledger=route_health,
        )
        if configured_key and configured_model
        else CognitiveModelGateway(client, model)
    )
    sensitive_data_approved = bool(
        configured_key
        and configured_model
        and settings.openrouter_data_collection == "deny"
        and settings.openrouter_zdr
    )
    registry = CapabilityRegistry()
    if configured_key and configured_model:
        registry.register(problem_representation_capability(engine))
    registry.register(problem_representation_capability(engine, deterministic_only=True))
    registry.register(constraint_discovery_capability(ConstraintDiscoveryEngine()))
    registry.register(calculator_capability())
    registry.register(human_input_capability())
    if semantic_memory is not None:
        registry.register(semantic_memory_capability(semantic_memory))
    registry.register(scenario_simulation_capability(gateway if sensitive_data_approved else None))
    registry.register(
        controlled_experiment_capability(gateway if sensitive_data_approved else None)
    )
    sources = AvailableDataSourceRegistry()
    sources.register(
        DataSourceDefinition(
            name="deterministic calculator",
            kind=DataSourceKind.CALCULATOR,
            description="Exact local arithmetic without a model or external network.",
            capability="calculator",
            approved_for_sensitive_data=True,
        )
    )
    sources.register(
        DataSourceDefinition(
            name="deterministic scenario simulation",
            kind=DataSourceKind.SIMULATION,
            description=(
                "Bounded exact sensitivity projections over explicit baselines, periods, "
                "rates, and thresholds."
            ),
            capability="simulator",
            approved_for_sensitive_data=True,
        )
    )
    sources.register(
        DataSourceDefinition(
            name="controlled numeric experiment evaluation",
            kind=DataSourceKind.EXPERIMENT,
            description=(
                "Evaluate explicit randomized independent control/treatment observations "
                "with effect size and uncertainty."
            ),
            capability="experiment",
            approved_for_sensitive_data=True,
        )
    )
    if settings.code_execution_enabled:
        registry.register(
            python_sandbox_capability(
                DockerPythonSandbox(
                    image=settings.code_execution_image,
                    limits=DockerSandboxLimits(
                        timeout_seconds=settings.code_execution_timeout_seconds,
                        memory_megabytes=settings.code_execution_memory_mb,
                    ),
                )
            )
        )
        sources.register(
            DataSourceDefinition(
                name="isolated Python execution",
                kind=DataSourceKind.CODE_EXECUTION,
                description=(
                    "Run bounded Python and assertions in an ephemeral networkless, "
                    "read-only, non-root container."
                ),
                capability="python_sandbox",
                risk_level=RiskLevel.MEDIUM,
            )
        )
    sources.register(
        DataSourceDefinition(
            name="focused human input",
            kind=DataSourceKind.HUMAN,
            description="Ask the user for an unavailable fact or decision boundary.",
            capability="human_input",
            approved_for_sensitive_data=True,
        )
    )
    configured_search_key = settings.search_api_key.get_secret_value().strip()
    requires_evidence_evaluator = False
    provider: SearchProvider | None = None
    if settings.search_provider.casefold() == "brave" and configured_search_key:
        provider = BraveSearchProvider(
            configured_search_key,
            base_url=settings.search_base_url,
        )
    elif (
        settings.search_provider.casefold() == "openrouter"
        and settings.openrouter_api_key.get_secret_value().strip()
        and configured_model
    ):
        provider = OpenRouterSearchProvider(settings)
    if provider is not None:
        model_backed_search = isinstance(provider, OpenRouterSearchProvider)
        registry.register(
            web_search_capability(
                provider,
                budget=ResearchBudget(
                    max_queries=settings.research_max_queries,
                    max_results_per_query=settings.research_max_results_per_query,
                    max_total_candidates=settings.research_max_total_candidates,
                ),
                prior_query_count=prior_research_query_count,
                max_model_calls=1 if model_backed_search else 0,
                max_output_tokens=SEARCH_OUTPUT_TOKEN_RESERVE if model_backed_search else 0,
                timeout_seconds=SEARCH_TIMEOUT_SECONDS if model_backed_search else 20.0,
                capability_version=provider.capability_version
                if isinstance(provider, OpenRouterSearchProvider)
                else None,
            )
        )
        requires_evidence_evaluator = True
        sources.register(
            DataSourceDefinition(
                name="bounded web search",
                kind=DataSourceKind.WEB_SEARCH,
                description=(
                    "Current public sources acquired under a query budget and evaluated "
                    "before evidence promotion."
                ),
                capability="web_search",
                risk_level=RiskLevel.LOW,
            )
        )
    configured_artifact_roots = [
        Path(item.strip())
        for item in settings.artifact_allowed_roots.split(pathsep)
        if item.strip()
    ]
    if enable_source_patch:
        if not settings.code_execution_enabled or not configured_artifact_roots:
            raise ValueError(
                "Source-patch investigation requires explicit execution and artifact permissions."
            )
        registry.register(
            source_patch_sandbox_capability(
                DockerPythonSandbox(
                    image=settings.code_execution_image,
                    limits=DockerSandboxLimits(
                        timeout_seconds=settings.code_execution_timeout_seconds,
                        memory_megabytes=settings.code_execution_memory_mb,
                    ),
                ),
                configured_artifact_roots,
            )
        )
        if configured_key and configured_model:
            registry.register(
                source_patch_investigator_capability(
                    gateway,
                    approved_for_sensitive_data=sensitive_data_approved,
                )
            )
    if configured_artifact_roots:
        inspector = LocalArtifactInspector(
            configured_artifact_roots,
            max_file_bytes=settings.artifact_max_file_bytes,
        )
        registry.register(local_artifact_capability(inspector))
        registry.register(
            table_measurement_capability(
                TableMeasurementTool(
                    configured_artifact_roots,
                    max_file_bytes=settings.artifact_max_file_bytes,
                )
            )
        )
        requires_evidence_evaluator = True
        sources.register(
            DataSourceDefinition(
                name="explicit local text artifact",
                kind=DataSourceKind.LOCAL_ARTIFACT,
                description=(
                    "A user-referenced text file contained by an approved local root; "
                    "no directory-wide implicit scanning."
                ),
                capability="inspector",
                approved_for_sensitive_data=True,
            )
        )
        sources.register(
            DataSourceDefinition(
                name="local CSV or JSON measurement",
                kind=DataSourceKind.MEASUREMENT,
                description=(
                    "Deterministic row counts, numeric distributions, percentiles, and "
                    "categorical frequencies from an explicitly referenced table."
                ),
                capability="measurement",
                approved_for_sensitive_data=True,
            )
        )
    if requires_evidence_evaluator:

        def memory_evidence_loader(query: str) -> list[EvidenceItem]:
            if semantic_memory is None:
                return []
            return [
                EvidenceItem(
                    source_type=f"memory:{item.source_type}",
                    source_uri=item.source_uri or f"memory://knowledge/{item.id}",
                    claim=item.content,
                    reliability_score=item.reliability_score,
                    relevance_score=item.similarity_score,
                )
                for item in semantic_memory.search_semantic(
                    query,
                    limit=3,
                    minimum_reliability=0.5,
                    minimum_similarity=0.08,
                )
            ]

        registry.register(
            evidence_evaluator_capability(
                gateway if configured_key and configured_model else None,
                model_approved_for_sensitive_data=sensitive_data_approved,
                memory_evidence_loader=memory_evidence_loader,
            )
        )
    for capability in on_demand_cognitive_capabilities(
        gateway,
        approved_for_sensitive_data=sensitive_data_approved,
    ):
        if capability.definition.kind is CapabilityKind.MODEL and not (
            configured_key and configured_model
        ):
            continue
        registry.register(capability)
    if configured_key and configured_model:
        registry.register(
            planner_capability(
                gateway,
                approved_for_sensitive_data=sensitive_data_approved,
                available_execution_tools=(
                    "calculator",
                    "simulator",
                    "experiment",
                    *(("python_sandbox",) if settings.code_execution_enabled else ()),
                    *(("measurement",) if configured_artifact_roots else ()),
                ),
            )
        )
    return CognitiveRuntime(
        registry,
        controller=CognitiveController(
            procedural_memory=procedural_memory,
            semantic_memory=semantic_memory,
            performance_policy=adaptive_ledger,
        ),
        budget=CognitiveResourceBudget(
            max_model_calls=settings.cognitive_max_model_calls,
            max_external_calls=settings.cognitive_max_external_calls,
            max_input_tokens=settings.cognitive_max_input_tokens,
            max_output_tokens=settings.cognitive_max_output_tokens,
            max_normalized_cost=settings.cognitive_max_normalized_cost,
            max_duration_ms=settings.cognitive_max_duration_ms,
        ),
        procedure_compiler=ProcedureCompiler(),
        performance_ledger=adaptive_ledger,
    )


def build_representation_session_runner(
    settings: Settings,
    *,
    mode_hint: ProductMode | None = None,
    domain_hint: str | None = None,
    prior_research_query_count: Callable[[str], int] | None = None,
    prior_evidence_loader: Callable[[str], list[EvidenceItem]] | None = None,
    semantic_memory: SemanticMemorySearch | None = None,
    procedural_memory: ProceduralPreferenceProvider | None = None,
    performance_ledger: CapabilityPerformanceLedger | None = None,
    semantic_route_health_ledger: SemanticRouteHealthLedger | None = None,
    progress_writer: Callable[[str, list[StateEvent]], None] | None = None,
) -> CognitiveSessionRunner:
    """Adapt the shared runtime to durable API session dispositions."""
    return CognitiveSessionRunner(
        build_cognitive_runtime(
            settings,
            mode_hint=mode_hint,
            domain_hint=domain_hint,
            prior_research_query_count=prior_research_query_count,
            semantic_memory=semantic_memory,
            procedural_memory=procedural_memory,
            performance_ledger=performance_ledger,
            semantic_route_health_ledger=semantic_route_health_ledger,
        ),
        evidence_loader=prior_evidence_loader,
        progress_writer=progress_writer,
    )
