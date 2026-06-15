# System 600 Platform

## Overview

The System 600 Platform is a version-controlled, machine-readable description of the System 600 building system.

It is not a BIM model, a product catalogue, or a supplier database. It is the system specification layer. It describes the abstract components, interfaces, rules, ports, tolerances, assembly sequences, evidence records, and checking logic that define how System 600 is intended to work.

The platform currently supports:

* structured YAML source data;
* validation of modules, parts, interfaces, rules and evidence;
* export to a consolidated JSON data package;
* a static web visualiser;
* GitHub Pages deployment;
* static wall-to-floor connection compatibility checking;
* design-level checking using small placed-instance fixtures.

The current development focus is wall-panel to floor-cassette connection compliance.

---

## What this repo is

This repository defines what System 600 allows.

It contains type-level system information such as:

* wall panel types;
* floor cassette types;
* generic parts;
* interface definitions;
* required ports;
* validation rules;
* prototype evidence;
* assembly sequences;
* platform-level limits and tolerances.

For example, a wall panel module records its dimensions, mass, lifting points, ports, permitted interfaces, validation rules and supporting evidence. A floor cassette records its plan dimensions, support-zone port, edge ports, lifting points and compatible interfaces. An interface records what module types it connects, what ports are required, what parts are used, and what geometric tolerances apply.

This allows the platform to answer questions such as:

```text
Can this wall type legally connect to this floor cassette type using this interface?
```

and, at design level:

```text
Does this placed wall–floor connection comply with the System 600 rules?
```

---

## What this repo is not

This repository should not contain:

* supplier names;
* factory locations;
* lead times;
* pricing;
* productivity figures;
* product SKUs;
* approved supplier variants;
* detailed geometry or mesh files;
* project-specific construction records.

Those belong in separate databases or project-instance repositories that reference this platform.

The platform defines what compliance means. Products and projects can later be checked against it.

---

## Current workflow

The platform follows this workflow:

```text
YAML source data
→ validate_platform.py
→ export_platform.py
→ system_600_platform.json
→ build_static_site.py
→ static visualiser
→ GitHub Pages
```

The YAML files are the source of truth. The JSON export and visualiser are generated outputs.

---

## Repository structure

```text
system-600-platform/
├── system/
│   └── platform.yaml
├── modules/
│   ├── wall_panels/
│   └── floor_cassettes/
├── parts/
├── interfaces/
├── rules/
├── evidence/
│   └── prototypes/
├── processes/
│   └── assembly_sequences/
├── designs/
├── docs/
├── scripts/
├── exports/
├── apps/
│   └── visualiser/
└── public/
```

## Key folders

### `system/`

Contains platform-wide settings, including:

* system ID and version;
* grid increments;
* permitted module sizes;
* tolerances;
* handling assumptions;
* maturity status.

### `modules/`

Contains System 600 module type definitions.

Current module families include:

* `wall_panels/`
* `floor_cassettes/`

These are type definitions, not project instances.

### `parts/`

Contains generic reusable parts, such as lifting inserts and connection brackets.

These are generic system parts, not supplier-specific products.

### `interfaces/`

Contains interface definitions between module types.

The current key interface is:

```text
IF_WALL_TO_FLOOR_001
```

This defines a wall-panel to floor-cassette connection.

### `rules/`

Contains System 600 rules and principles.

These include grid rules, lifting rules, interface rules, services rules, façade rules and component-granularity rules.

### `evidence/`

Contains prototype evidence records.

Evidence records link tests, prototypes and findings back to system objects.

### `processes/`

Contains reusable process definitions.

The current process family is:

```text
assembly_sequences/
```

Assembly sequences define the recommended order of operations for installing or assembling parts of the system.

### `designs/`

Contains small design-instance fixtures used for checking.

Design files are separate from the platform specification. They describe placed instances of platform types.

### `scripts/`

Contains validation, export, build and checking scripts.

### `exports/`

Contains the generated platform JSON package.

### `apps/visualiser/`

Contains the source HTML for the graph visualiser.

### `public/`

Contains the built static site that is deployed to GitHub Pages.

---

## Setup

This project uses plain Python and PyYAML.

Create and activate a virtual environment:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install PyYAML
```

---

## Validate the platform

Run:

```powershell
python scripts\validate_platform.py
```

Expected output:

```text
Validation passed.
```

The validator checks things such as:

* module dimensions against permitted platform sizes;
* lifting capacity;
* part references;
* interface references;
* rule references;
* evidence references;
* interface connection methods;
* whether required interface ports resolve across module types.

For the wall-to-floor interface, the validator checks that:

```text
wall_panel provides base
floor_cassette provides support_zone
both module types allow IF_WALL_TO_FLOOR_001
```

---

## Export the platform

Run:

```powershell
python scripts\export_platform.py
```

This creates:

```text
exports/system_600_platform.json
```

The export packages modules, parts, interfaces, rules, evidence and assembly sequences into one JSON file.

---

## Build the visualiser

Run:

```powershell
python scripts\build_static_site.py
```

This creates the deployable static site in:

```text
public/
```

To view locally:

```powershell
python -m http.server 8000 -d public
```

Then open:

```text
http://localhost:8000
```

---

## Full build pipeline

Run:

```powershell
python scripts\validate_platform.py
python scripts\export_platform.py
python scripts\build_static_site.py
```

This should be run before committing major changes.

---

# Wall–floor connection checker

The repository now includes a static wall–floor connection checker.

It answers:

```text
Can this wall type legally connect to this floor type using this interface?
```

The checker does not use coordinates. It checks type-level compatibility only.

Run:

```powershell
python scripts\check_connection.py WALL_2400_2700_EXT_A FLOOR_2400_6000_STRUCT_A IF_WALL_TO_FLOOR_001
```

Expected result:

```json
"compliant": true
```

A deliberate failing example:

```powershell
python scripts\check_connection.py WALL_2400_2700_EXT_A WALL_1200_2700_EXT_A IF_WALL_TO_FLOOR_001
```

Expected result:

```json
"compliant": false
```

This fails because the second module is a wall panel, not a floor cassette, and it does not provide the required `support_zone` port.

---

## Static checks

The static checker evaluates:

* selected wall type exists;
* selected floor type exists;
* selected interface exists;
* interface `from_module_type` matches the wall type;
* interface `to_module_type` matches the floor type;
* wall lists the interface in `allowed_interfaces`;
* floor lists the interface in `allowed_interfaces`;
* required wall-side port exists;
* required floor-side port exists;
* interface connection methods resolve to real parts;
* module sizes are permitted;
* modules declare grid alignment.

Each check returns:

```json
{
  "rule": "...",
  "passed": true,
  "detail": "..."
}
```

The checker returns structured results, not just a bare true/false value.

---

# Design-level checker

The repository also includes a design-level checker.

It answers:

```text
Does this placed design comply with the System 600 wall–floor connection rules?
```

Design fixtures live in:

```text
designs/
```

Current fixtures:

```text
SAMPLE_DESIGN_PASS_001.yaml
SAMPLE_DESIGN_FAIL_001.yaml
```

Run the passing design:

```powershell
python scripts\check_design.py designs\SAMPLE_DESIGN_PASS_001.yaml
```

Expected result:

```json
"compliant": true
```

Run the failing design:

```powershell
python scripts\check_design.py designs\SAMPLE_DESIGN_FAIL_001.yaml
```

Expected result:

```json
"compliant": false
```

The failing fixture deliberately places the wall off the 600 mm grid.

---

## Design checks

The design checker:

1. loads a design YAML file;
2. resolves each design instance to a platform type;
3. runs the static wall–floor connection checker;
4. evaluates grid alignment using placed instance coordinates;
5. evaluates edge distance where a connection point is provided;
6. evaluates tolerance envelope where declared offsets are provided;
7. returns per-connection and overall compliance results.

If a geometric rule needs information that is missing, the checker reports that clearly rather than silently assuming a value.

---

## Run all checker examples

Run:

```powershell
python scripts\run_connection_checker_examples.py
```

This runs both the passing and failing design fixtures and prints a readable summary.

---

# Current System 600 objects

## Wall panels

```text
WALL_1200_2700_EXT_A
WALL_2400_2700_EXT_A
```

## Floor cassettes

```text
FLOOR_1200_2400_STRUCT_A
FLOOR_2400_6000_STRUCT_A
```

## Interface

```text
IF_WALL_TO_FLOOR_001
```

## Key parts

```text
PART_LIFTING_INSERT_M16_001
PART_SLOTTED_BASE_BRACKET_001
```

## Assembly sequence

```text
ASSEMBLY_WALL_FLOOR_001
```

---

# Development conventions

## Source of truth

Edit YAML source files, not generated JSON.

The source-of-truth files are mainly:

```text
system/
modules/
parts/
interfaces/
rules/
evidence/
processes/
designs/
```

Generated outputs include:

```text
exports/
public/
```

## Naming conventions

Use stable IDs:

```text
WALL_*
FLOOR_*
IF_*
PART_*
RULE_*
ASSEMBLY_*
PROTO_*
```

Do not rename existing IDs unless there is a deliberate migration plan.

## No supplier data

Do not add supplier-specific data to this repository.

Avoid fields such as:

```text
supplier
factory
lead_time
price
sku
approved_product
product_variant
```

Those belong in a separate product database.

## No project-specific construction records

Do not put actual installation dates, worker names, site QA records, project defects or construction photos into the platform specification.

Those belong in future project-instance or execution-record layers.

---

# Typical development workflow

Before editing:

```powershell
git status
git pull
```

After editing:

```powershell
python scripts\validate_platform.py
python scripts\export_platform.py
python scripts\build_static_site.py
```

Then:

```powershell
git status
git add .
git commit -m "Describe the change"
git push
```

---

# Current development status

Implemented:

* platform YAML structure;
* wall panel module family;
* floor cassette module family;
* generic parts;
* wall-to-floor interface;
* validation rules;
* prototype evidence;
* assembly sequence support;
* JSON export;
* static visualiser;
* GitHub Pages deployment;
* static wall–floor connection checker;
* design-level checker;
* passing and failing design fixtures.

Next likely work:

* improve README and documentation;
* add standard operating procedures linked to assembly steps;
* refine geometric design-checking conventions;
* add more realistic floor, wall and interface types;
* improve visualiser support for checking and design-layer concepts;
* add a lightweight results viewer for checker outputs.
