"""CLI sub-commands for the CELINE mapper: validate-spec, map, shacl-check, inspect."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml

mapper_app = typer.Typer(name="mapper", help="Declarative mapping: spec authoring & validation.")


@mapper_app.command("validate-spec")
def cmd_validate_spec(
    spec_path: Path = typer.Argument(..., help="Path to a MappingSpec YAML file."),
) -> None:
    """Validate a MappingSpec YAML against the JSON Schema."""
    from celine.mapper.spec import MappingSpecLoader, SpecValidationError  # noqa: PLC0415

    try:
        spec = MappingSpecLoader().load(spec_path)
        typer.echo(
            f"✓ {spec_path.name}  →  {spec.target_type}  "
            f"({len(spec.fields)} fields)"
        )
    except SpecValidationError as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(1)


@mapper_app.command("map")
def cmd_map(
    spec_path: Path = typer.Argument(..., help="Path to a MappingSpec YAML file."),
    input_path: Path = typer.Argument(..., help="JSON file: a single dict or list of dicts."),
    context_json: Optional[str] = typer.Option(
        None, "--context", "-c",
        help='JSON object with context variables, e.g. \'{"community_key": "it-folgaria"}\'',
    ),
    output_path: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write JSON-LD document to this file instead of stdout."
    ),
) -> None:
    """Map input rows to JSON-LD nodes using the given spec."""
    from celine.mapper.output_mapper import OutputMapper  # noqa: PLC0415
    from celine.mapper.graph import CelineGraphBuilder  # noqa: PLC0415

    context: dict = json.loads(context_json) if context_json else {}

    with input_path.open() as fh:
        data = json.load(fh)
    rows = data if isinstance(data, list) else [data]

    mapper = OutputMapper.from_yaml_path(spec_path, context=context)
    nodes = mapper.map_many(rows)

    builder = CelineGraphBuilder()
    document = builder.build_document(nodes)

    output = json.dumps(document, indent=2, ensure_ascii=False)
    if output_path:
        output_path.write_text(output)
        typer.echo(f"Written to {output_path}")
    else:
        typer.echo(output)


@mapper_app.command("shacl-check")
def cmd_shacl_check(
    spec_path: Path = typer.Argument(..., help="Path to a MappingSpec YAML file."),
    input_path: Path = typer.Argument(..., help="JSON file: a single dict or list of dicts."),
    context_json: Optional[str] = typer.Option(
        None, "--context", "-c",
        help='JSON object with context variables.',
    ),
) -> None:
    """Map input rows, build a JSON-LD document, and run SHACL validation."""
    from celine.mapper.output_mapper import OutputMapper  # noqa: PLC0415
    from celine.mapper.graph import CelineGraphBuilder  # noqa: PLC0415

    context: dict = json.loads(context_json) if context_json else {}

    with input_path.open() as fh:
        data = json.load(fh)
    rows = data if isinstance(data, list) else [data]

    mapper = OutputMapper.from_yaml_path(spec_path, context=context)
    nodes = mapper.map_many(rows)

    builder = CelineGraphBuilder()
    document = builder.build_document(nodes)

    try:
        builder.validate_json_schema(document)
        typer.echo("✓ JSON Schema validation passed")
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"✗ JSON Schema validation failed: {exc}", err=True)
        raise typer.Exit(1)

    rdf_graph = builder.to_rdf_graph(document)
    result = builder.validate_shacl(rdf_graph)

    if result.conforms:
        typer.echo(f"✓ SHACL validation passed  ({len(nodes)} nodes)")
    else:
        typer.echo("✗ SHACL validation failed:", err=True)
        for v in result.violations:
            typer.echo(f"  {v}", err=True)
        raise typer.Exit(1)


@mapper_app.command("inspect")
def cmd_inspect(
    spec_path: Path = typer.Argument(..., help="Path to a MappingSpec YAML file."),
) -> None:
    """Pretty-print a parsed MappingSpec as a table."""
    from celine.mapper.spec import MappingSpecLoader  # noqa: PLC0415

    spec = MappingSpecLoader().load(spec_path)

    typer.echo(f"Spec:         {spec_path.name}")
    typer.echo(f"Version:      {spec.version}")
    typer.echo(f"Target type:  {spec.target_type}")
    typer.echo(f"ID template:  {spec.id_template}")
    if spec.label_template:
        typer.echo(f"Label:        {spec.label_template}")
    if spec.context_vars:
        typer.echo(f"Context vars: {', '.join(spec.context_vars)}")
    typer.echo(f"\n{'source':<25} {'kind':<10} {'target':<40} {'req':<5} {'datatype'}")
    typer.echo("-" * 95)
    for fm in spec.fields:
        src = fm.source or "(constant)"
        typer.echo(
            f"{src:<25} {fm.kind:<10} {fm.target:<40} {'✓' if fm.required else '':<5} "
            f"{fm.datatype or ''}"
        )
        if fm.kind == "nested" and fm.nested_fields:
            for nf in fm.nested_fields:
                nsrc = nf.source or "(constant)"
                typer.echo(
                    f"  └─ {nsrc:<21} {nf.kind:<10} {nf.target:<40} "
                    f"{'✓' if nf.required else '':<5} {nf.datatype or ''}"
                )
