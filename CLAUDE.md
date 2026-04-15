# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package Context

This is **imio.dms.mail**, the core Plone 4.3 / Python 2.7 DMS package for incoming and outgoing mail management. Build, test, and linting commands are documented in the parent repo's CLAUDE.md (`server.dmsmail/CLAUDE.md`).

## Architecture

### Content Types

3 active Dexterity content types defined in `dmsmail.py`:
- `ImioDmsIncomingMail` / `ImioDmsIncomingEmail` — received mail/email
- `ImioDmsOutgoingMail` — sent mail (`ImioDmsOutgoingEmail` exists in code but is not used)

Schemas are extended via behaviors in `content/behaviors.py` (signing, local roles, data transfer, category defaults). Type XML overrides live in `profiles/default/types/`.

### Key Module Responsibilities

| Module | Purpose |
|---|---|
| `setuphandlers.py` | GenericSetup install/upgrade steps and migration orchestration |
| `adapters.py` | Schema adapters, catalog indexers, local role providers |
| `subscribers.py` | Event handlers (object added/modified, workflow transitions) |
| `wfadaptations.py` | Workflow variant definitions (service validation, approval chains) |
| `steps.py` | Workflow step processors invoked by transitions |
| `utils.py` | `VariousUtilsMethods`, `IdmUtilsMethods`, `OdmUtilsMethods` helper classes |
| `vocabularies.py` | 35+ named vocabulary factories |
| `columns.py` | Table column classes for listing views |
| `examples.py` | Demo/test data generation |
| `relations_utils.py` | Relation tracking and cleanup helpers |

### Browser Layer (`browser/`)

- `views.py` — main view classes (autocomplete, SSE, email sending, REST client)
- `actionspanel.py` — actions/transitions panel (the largest file, ~21K lines)
- `batchactions.py` — bulk operations on document sets
- `table.py` — filterable table rendering
- `settings.py` — control panel (`IImioDmsMailConfig` registry interface)
- `documentgenerator.py` — POD template generation wrappers
- `task.py`, `reply_form.py`, `viewlets.py` — task views, reply forms, layout viewlets
- Templates in `browser/templates/` (Chameleon `.pt` files)
- Icons and JS in `browser/static/`

### ZCML Layout

`configure.zcml` is the entry point; it includes:
`adapters.zcml`, `columns.zcml`, `vocabularies.zcml`, `subscribers.zcml`, `profiles.zcml`, `skins.zcml`, `overrides.zcml`

### Workflows

4 workflows in `profiles/default/workflows/`:
- `incomingmail_workflow` — main workflow for incoming mail processing
- `outgoingmail_workflow` — main workflow for outgoing mail lifecycle
- `active_inactive_workflow` and `internal_application_workflow` — rarely used, applied to auxiliary types

Workflow variants (additional states/transitions grafted onto the base workflows) are registered via `wfadaptations.py` using `collective.wfadaptations`.

### Permission Model

Two custom permissions control field-level write access:
- `imio.dms.mail: Write base fields`
- `imio.dms.mail: Write treating group field`

Local roles are provided dynamically by adapters in `adapters.py` using `borg.localrole`. Group-based access is managed via `collective.contact.plonegroup` (service groups: encodeur, editeur, n_plus_1, etc.).

### Migrations

Upgrade steps live in `migrations/` (one module per version: `migrate_to_1_0.py` … `migrate_to_3_1_2.py`). They are registered as GenericSetup upgrade steps in `profiles.zcml` and called by `setuphandlers.py`.

### Testing

Tests are in `tests/`. The integration layer is `DMSMAIL_INTEGRATION_TESTING` from `testing.py`. Permission-specific tests share fixtures from `tests/permissions_base.py`. Robot Framework tests are under `tests/robot/`.

Use `mock` only when a dependency cannot be set up in a real Plone integration environment.

### GenericSetup Profiles

- `default` — main install (types, workflows, catalog, registry, portlets, rolemap)
- `examples` — full demo data
- `examples-minimal` — minimal test data
- `testing` — test-only configuration
- `singles` — à-la-carte import steps (see below)

### Singles Steps (ZMI Advanced Imports)

The `singles` profile contains standalone import steps that are **not** run during normal install or upgrade. They are applied manually via the ZMI: `portal_setup` → *Import* tab → select profile `imio.dms.mail (singles)` → tick the desired step → *Import selected steps*.

| Step ID | Purpose |
|---|---|
| `imiodmsmail-activate-esigning` | Activates approbation and e-signing functionality (adds `to_approve` OM workflow adaptation, configures `imio.esign`) |
| `imiodmsmail-configure-demo-site` | Applies demo-site configuration (branding, demo users, sample data layout) |
| `imiodmsmail-om_to_approve_wfadaptation` | Adds the `to_approve` state to `outgoingmail_workflow` independently of the esigning stack |
| `imiodmsmail-om_n_plus_1_wfadaptation` / `imiodmsmail-im_n_plus_1_wfadaptation` | Adds n+1 hierarchical validation level to OM/IM workflows |
| `imiodmsmail-om_to_print_wfadaptation` | Adds print-queue state to `outgoingmail_workflow` |
| `imiodmsmail-activate_classification` / `imiodmsmail-deactivate_classification` | Toggles `collective.classification` integration |
| `imiodmsmail-create-persons-from-users` | Creates `Person`/`HeldPosition` objects from existing Plone users (internal staff) |
| `imiodmsmail-contact-import-pipeline` | Configures the `collective.contact.importexport` transmogrifier pipeline |
| `imiodmsmail-configure-wsclient` | Configures `imio.pm.wsclient` (PloneMeeting integration) |
