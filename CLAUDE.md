# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package Context

This is **imio.dms.mail**, the core Plone 4.3 / Python 2.7 DMS package for incoming and outgoing mail management. Build and test commands are documented in the parent repo's CLAUDE.md (`server.dmsmail/CLAUDE.md`).

## Gotchas

- `ImioDmsOutgoingEmail` exists in code but is not used: only `ImioDmsIncomingMail`, `ImioDmsIncomingEmail` and `ImioDmsOutgoingMail` are active.
- Workflow variants (additional states/transitions grafted onto the base workflows) are registered via `wfadaptations.py` using `collective.wfadaptations`.

## Testing

Use `mock` only when a dependency cannot be set up in a real Plone integration environment.

## Singles Steps (ZMI Advanced Imports)

The `singles` profile contains standalone import steps that are **not** run during normal install or upgrade. They are applied manually via the ZMI: `portal_setup` → *Import* tab → select profile `imio.dms.mail (singles)` → tick the desired step → *Import selected steps*.

| Step ID                                                                         | Purpose                                                                                                                 |
|---------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| `imiodmsmail-activate-om-signing`                                               | Activates approbation and e-signing functionality (adds `to_approve` OM workflow adaptation, configures `imio.esign`)   |
| `imiodmsmail-activate-sign-request`                                             | Activates signing-request functionality (adds the `demand_sign` "Demande Sign." plonegroup function)                    |
| `imiodmsmail-configure-demo-site`                                               | Applies demo-site configuration (branding, demo users, sample data layout)                                              |
| `imiodmsmail-om_to_approve_wfadaptation`                                        | Adds the `to_approve` state to `outgoingmail_workflow` independently of the esigning stack                              |
| `imiodmsmail-om_n_plus_1_wfadaptation` / `imiodmsmail-im_n_plus_1_wfadaptation` | Adds n+1 hierarchical validation level to OM/IM workflows                                                               |
| `imiodmsmail-om_to_print_wfadaptation`                                          | Adds print-queue state to `outgoingmail_workflow`                                                                       |
| `imiodmsmail-activate_classification` / `imiodmsmail-deactivate_classification` | Toggles `collective.classification` integration                                                                         |
| `imiodmsmail-create-persons-from-users`                                         | Creates `Person`/`HeldPosition` objects from existing Plone users (internal staff)                                      |
| `imiodmsmail-contact-import-pipeline`                                           | Configures the `collective.contact.importexport` transmogrifier pipeline                                                |
| `imiodmsmail-configure-wsclient`                                                | Configures `imio.pm.wsclient` (PloneMeeting integration)                                                                |
