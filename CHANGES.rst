Changelog
=========

1.0 (unreleased)
----------------

- Replaced collection view and main portlet by dashboard and collectionwidget portlet
  [sgeulette]

- Setup task workflow, task local roles configuration, task collections
  [sgeulette]

- Protect treating_groups field by write permission
  [sgeulette]

- Added batch change on selected items: state change, treating group change, assigned user change
  [sgeulette]

- Use elephantvocabulary of plonegroup
  [sgeulette]

- Added robot tests for screenshots
  [sgeulette]

- Upgraded and migrated collective.behavior.talcondition. Added conditions on some state collections.
  [sgeulette]

- Added unit tests to improve coverage
  [sgeulette]

- Upgraded collective.contact.plonegroup. Removed deprecated interfaces usage.
  [sgeulette]

- Include querynextprev, messagesviewlet
  [sgeulette]

- Some improvements: contact add width, also validateur in assigned user, changed default position types,
                     actions panel transition configuration, corrected listing, removed adding mainfile from menu,
                     colorized collection results, removed grok, improved assigned user warning, front page text,
                     set undo visible, improved state colorization, changed configlet and view permissions, added reorder on mail types,
                     added link to plonegroup-organization, improved localroles config column width, ckeditor configuration,
                     original mail date requirement option, revert to previous version only for manager
  [sgeulette]


0.3.1 (2015-06-03)
------------------

- Add an optional condition on propose_to_agent transition to check assigned_user completion before proposing mail to agent
  [sgeulette]

- On created collection, add locked icon and auto-refresh
  [sgeulette]

- Add "close" transition from "proposed_to_agent" (bypass "in_treatment")
  [sgeulette]

- Add more relevant columns in collections
  [sgeulette]

- Use collective.compoundcriterion and collective.behavior.talcondition
  [sgeulette]

- Use imio.history
  [sgeulette]

- Use imio.actionspanel
  [sgeulette]

- Move collections
  [sgeulette]

- Begin collective.task integration
  [sgeulette]

- Set color by state
  [sgeulette]

- Activate locking on incomingmail
  [sgeulette]

- Protect some incomingmail attributes edition by a permission
  [sgeulette, anuyens]

0.3 (2015-02-25)
----------------

- Upgrade step
  [sgeulette]

- Corrected listing view.
  [sgeulette]

- Remove portlet methods memoize.
  [sgeulette]

- Updated translations, configuration, tests.
  [sgeulette]

- Use now dexterity.localrolesfield in schema.
  [sgeulette]

- Added scan fields.
  [sgeulette]

- Use dmsdocument-edit view (file preview in modification).
  [sgeulette]


0.2 (2014-02-14)
----------------

- Added documentviewer configuration
  [sgeulette]

- Added topics
  [sgeulette]

- Added internal application workflow
  [sgeulette]

- Upgrade step
  [sgeulette]

- Added general manager role, encodeurs group 
  [sgeulette]

- Updated treating_groups and recipient_groups configuration
  [sgeulette]

- Added incoming mail workflow for localrolefield
  [sgeulette]


0.1
---
- DmsIncomingMail overrides, adding field
  [sgeulette]
- Site customization
  [sgeulette]
- Basic data
  [sgeulette]
- Tests
  [sgeulette]
- Added basic workflow
  [sgeulette]
- Add settings form
  [sgeulette]
- Updated internal_reference_no metadata
  [sgeulette]
- Show treating_groups again but patch set method to avoid setting local roles
  [sgeulette]
