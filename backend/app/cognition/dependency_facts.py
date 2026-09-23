"""Experimental source-fact coverage for supplied Python dependency investigations.

This is a necessary coverage check, not a semantic verifier or a package resolver.
It reads admitted snapshots only and never evaluates environment markers locally.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version
from pydantic import JsonValue

from app.graph.state import PolyaState
from app.models.contracts import EvidenceItem

DEPENDENCY_FACTS_VERSION = "dependency_source_facts@0.2.0"
LIMITATION = (
    "Necessary source-fact coverage only; not proof of prose consistency, advisory "
    "reachability, later-version safety, or resolver compatibility. Environment markers "
    "and optional groups are preserved, not evaluated against this machine."
)
INSTRUCTIONS = (
    "When dependency_source_facts applies, use its source-bound comparisons. Include "
    "every required_fact verbatim in a compact Source facts block in final_answer, with "
    "its source reference. Do not contradict those facts elsewhere. A listed fix version "
    "is not proof that all later versions are safe or that the full graph resolves. "
    "If errors are present, verification must fail; do not invent missing source facts."
)


@dataclass(frozen=True)
class DependencyFact:
    statement: str
    source_uri: str


@dataclass
class DependencyFacts:
    applicable: bool = False
    facts: list[DependencyFact] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def context(self) -> dict[str, JsonValue]:
        return {
            "dependency_source_facts": {
                "version": DEPENDENCY_FACTS_VERSION,
                "applicable": self.applicable,
                "required_facts": [
                    {"statement": fact.statement, "source_uri": fact.source_uri}
                    for fact in self.facts
                ],
                "errors": list(self.errors),
                "limitation": LIMITATION,
            }
        }

    def failures(self, answer: str) -> list[str]:
        if not self.applicable:
            return []
        normalized = " ".join(answer.split())
        return [
            *self.errors,
            *[
                f"Missing required source fact: {fact.statement} ({fact.source_uri})"
                for fact in self.facts
                if " ".join(fact.statement.split()) not in normalized
            ],
        ]


def _snapshot(item: EvidenceItem) -> str:
    """Decode the inspector's complete numbered snapshot, rejecting missing lines."""
    lines = (item.raw_excerpt or "").splitlines()
    match = re.fullmatch(
        r"\[Source coverage: complete file; total lines: (\d+)\]", lines[0] if lines else ""
    )
    if not match or int(match[1]) != len(lines) - 1:
        raise ValueError("incomplete or unsupported snapshot")
    content = []
    for index, line in enumerate(lines[1:], 1):
        prefix = f"{index}: "
        if not line.startswith(prefix):
            raise ValueError("snapshot line provenance is incomplete")
        content.append(line[len(prefix) :])
    return "\n".join(content)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object keys")
        result[key] = value
    return result


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError("expected a string list")
    return value


def _fixes(audit: dict[str, Any]) -> dict[str, set[Version]]:
    if "affected_packages" in audit and "dependencies" in audit:
        raise ValueError("ambiguous audit package collections")
    packages = audit.get("affected_packages", audit.get("dependencies"))
    if not isinstance(packages, list):
        raise ValueError("unsupported dependency audit")
    fixes: dict[str, set[Version]] = {}
    for package in packages:
        if not isinstance(package, dict) or not isinstance(package.get("name"), str):
            raise ValueError("invalid audited package")
        vulns = package.get("vulns")
        if not isinstance(vulns, list):
            raise ValueError("missing vulnerability records")
        if not vulns:
            continue
        name = canonicalize_name(package["name"], validate=True)
        versions = fixes.setdefault(name, set())
        for vuln in vulns:
            if not isinstance(vuln, dict):
                raise ValueError("invalid vulnerability record")
            versions.update(Version(value) for value in _strings(vuln.get("fix_versions")))
    return fixes


def _comparison(requirement: Requirement, fixes: set[Version]) -> str:
    if requirement.url:
        return "uses a direct URL; listed-fix compatibility is unresolved"
    admitted = sorted(
        version for version in fixes if requirement.specifier.contains(version, prereleases=True)
    )
    excluded = sorted(fixes.difference(admitted))
    if not fixes:
        return "the supplied audit lists no fix version"
    clauses = []
    if admitted:
        clauses.append("admits listed fix versions " + ", ".join(map(str, admitted)))
    if excluded:
        clauses.append("excludes listed fix versions " + ", ".join(map(str, excluded)))
    return "; ".join(clauses)


def _inventory(audit: dict[str, Any]) -> str:
    """Count scanner records and alias components without conflating their identities."""
    packages: set[str] = set()
    scanner_ids: set[str] = set()
    components: list[set[str]] = []
    records = 0
    for package in audit.get("affected_packages", audit.get("dependencies", [])):
        for vuln in package["vulns"]:
            identifier = vuln.get("id")
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError("missing scanner identity")
            packages.add(canonicalize_name(package["name"]))
            records += 1
            scanner_ids.add(identifier)
            group = {identifier, *_strings(vuln.get("aliases", []))}
            if any(not alias.strip() for alias in group):
                raise ValueError("empty advisory alias")
            remaining = []
            for existing in components:
                if existing.intersection(group):
                    group.update(existing)
                else:
                    remaining.append(existing)
            components = [*remaining, group]
    return (
        f"Supplied audit inventory: {len(packages)} affected packages; {records} vulnerability "
        f"records; {len(scanner_ids)} distinct scanner IDs; {len(components)} connected "
        "ID/alias groups. Alias groups reflect supplied links, not independently confirmed identity."
    )


def dependency_source_facts(state: PolyaState) -> DependencyFacts:
    """Compile known source shapes, without inferring facts from model summaries."""
    result = DependencyFacts()
    task = state["raw_input"].casefold()
    if not re.search(r"\b(?:dependenc\w*|packages?|remediat\w*)\b", task) or not re.search(
        r"\b(?:constraints?|bounds?|pins?|pinned|compatible|compatibility)\b", task
    ):
        return result
    documents: list[tuple[str, dict[str, Any], str]] = []
    seen: dict[str, str] = {}
    size = 0
    for item in state["evidence"]:
        uri = item.source_uri or ""
        path = urlsplit(uri).path.casefold()
        if item.source_type != "evaluated_local_artifact" or not path.endswith((".json", ".toml")):
            continue
        size += len(item.raw_excerpt or "")
        if size > 100_000 or len(documents) >= 5:
            result.errors.append("Dependency snapshot inspection limit exceeded.")
            break
        try:
            content = _snapshot(item)
            identity = uri.split("#", 1)[0]
            if identity in seen:
                if seen[identity] != content:
                    raise ValueError("conflicting snapshots of one source")
                continue
            seen[identity] = content
            data = (
                tomllib.loads(content)
                if path.endswith(".toml")
                else json.loads(content, object_pairs_hook=_unique_object)
            )
            if not isinstance(data, dict):
                raise ValueError("expected an object document")
            role = "other"
            if "affected_packages" in data or "dependencies" in data:
                role = "audit"
            elif "project" in data:
                role = "project"
            elif data and any(
                isinstance(value, dict) and "requires" in value for value in data.values()
            ):
                role = "installed"
            documents.append((role, data, uri))
        except ValueError, TypeError, RecursionError:
            result.errors.append(
                f"Cannot establish complete unambiguous dependency facts from {uri}."
            )
    audits = [(data, uri) for role, data, uri in documents if role == "audit"]
    # A recognized audit activates this narrowly scoped check. Unknown tasks retain
    # the semantic path and must not be represented as deterministically verified.
    result.applicable = bool(audits)
    if not result.applicable:
        return result
    projects = [(data, uri) for role, data, uri in documents if role == "project"]
    installed = [(data, uri) for role, data, uri in documents if role == "installed"]
    if len(audits) != 1 or len(projects) != 1 or len(installed) > 1:
        result.errors.append(
            "Constraint facts require one audit, one project manifest, and at most one installed snapshot."
        )
        return result
    try:
        fixes = _fixes(audits[0][0])
        if re.search(r"\b(?:advisories|advisory|deduplicat\w*|duplicates?)\b", task):
            result.facts.append(DependencyFact(_inventory(audits[0][0]), audits[0][1]))
        project, project_uri = projects[0]
        metadata = project["project"]
        if not isinstance(metadata, dict):
            raise ValueError("invalid project metadata")
        declarations: list[tuple[str, str]] = [
            (requirement, "project.dependencies")
            for requirement in _strings(metadata.get("dependencies", []))
        ]
        optional = metadata.get("optional-dependencies", {})
        if not isinstance(optional, dict):
            raise ValueError("invalid optional dependencies")
        for group, requirements in optional.items():
            declarations.extend(
                (requirement, f"project.optional-dependencies.{group}")
                for requirement in _strings(requirements)
            )
        if {"dependencies", "optional-dependencies"}.intersection(
            _strings(metadata.get("dynamic", []))
        ):
            raise ValueError("dynamic dependencies are not supported")
        for raw, group in declarations:
            requirement = Requirement(raw)
            versions = fixes.get(canonicalize_name(requirement.name))
            if versions is not None:
                result.facts.append(
                    DependencyFact(
                        f"Declared {group}: {raw}; {_comparison(requirement, versions)}.",
                        project_uri,
                    )
                )
        for snapshot, uri in installed:
            parents: set[str] = set()
            for parent, package in snapshot.items():
                normalized = canonicalize_name(parent, validate=True)
                if normalized in parents or not isinstance(package, dict):
                    raise ValueError("ambiguous installed parent")
                parents.add(normalized)
                parent_version = Version(package["version"])
                for raw in _strings(package.get("requires")):
                    requirement = Requirement(raw)
                    versions = fixes.get(canonicalize_name(requirement.name))
                    if versions is not None:
                        result.facts.append(
                            DependencyFact(
                                f"Installed parent {parent}=={parent_version} declares {raw}; {_comparison(requirement, versions)}.",
                                uri,
                            )
                        )
        if not result.facts:
            result.errors.append(
                "No audited dependency could be linked to the supplied constraints."
            )
        if len(result.facts) > 40:
            result.facts.clear()
            result.errors.append("Dependency fact count exceeds the bounded review limit.")
    except ValueError, TypeError, KeyError, InvalidRequirement, InvalidVersion:
        result.facts.clear()
        result.errors.append(
            "Dependency source schema or requirement/version is invalid or unsupported."
        )
    return result
