"""Guard the binding PolyaBrain product identity across builder entrypoints."""

import re
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
IDENTITY_DOCUMENTS = (
    "AGENTS.md",
    "README.md",
    "PolyaBrain_Product_Implementation_Master_Plan.md",
    "docs/README.md",
    "docs/00_vision/Cognitive_Product_Doctrine.md",
    "docs/00_vision/PolyaBrain_Final_Foundational_Design.md",
    "docs/00_vision/PolyaBrain_Vision_Summary.md",
    "docs/01_architecture/MVP_Architecture_Decisions.md",
    "docs/architecture_decisions.md",
    "docs/03_implementation/Chapter_1_Start_Here.md",
    "docs/03_implementation/Product_Acceleration_Playbook.md",
)
REQUIRED_LAYER_TERMS = (
    "PolyaBrain Investigator",
    "Cognitive Runtime",
    "Intelligence OS",
)
RETIRED_PRODUCT_CLAIMS = (
    "PolyaBrain Core Platform is the product",
    "Build PolyaBrain Core Platform first",
)
HUMAN_PRODUCT_TERMS = (
    "brain-inspired problem-solving intelligence system",
    "cognitive workbench",
    "reasoning visible",
    "evidence inspectable",
    "uncertainty explicit",
    "learning reusable",
)


@pytest.mark.parametrize("relative_path", IDENTITY_DOCUMENTS)
def test_primary_builder_docs_preserve_product_runtime_and_os_layers(
    relative_path: str,
) -> None:
    content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
    normalized_content = re.sub(r"\s+", " ", content)

    for term in REQUIRED_LAYER_TERMS:
        assert term in normalized_content, f"{relative_path} is missing identity term: {term}"


def test_retired_platform_first_claims_do_not_reappear() -> None:
    combined = re.sub(
        r"\s+",
        " ",
        "\n".join(
            (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            for relative_path in IDENTITY_DOCUMENTS
        ),
    )

    for retired_claim in RETIRED_PRODUCT_CLAIMS:
        assert retired_claim not in combined


@pytest.mark.parametrize(
    "relative_path",
    (
        "AGENTS.md",
        "README.md",
        "PolyaBrain_Product_Implementation_Master_Plan.md",
        "docs/00_vision/Cognitive_Product_Doctrine.md",
    ),
)
def test_primary_identity_docs_preserve_the_human_product_definition(
    relative_path: str,
) -> None:
    content = re.sub(
        r"\s+",
        " ",
        (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8"),
    ).casefold()

    for term in HUMAN_PRODUCT_TERMS:
        assert term in content, f"{relative_path} is missing human product term: {term}"
