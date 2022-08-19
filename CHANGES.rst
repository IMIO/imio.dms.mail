Changelog
=========

3.0.31
------

- Can reply on "created" state
- Corrected overiddes in zcml so tests can be run again
- Added a specific RemoteLibrary with "get_mail_path" function to find a mail from its id or title.
  So doc.robot and video-doc.robot can be run again
- Replaced "get_groups" & "getGroups" by "get_plone_groups_for_user"
- Replaced "get_selected_org_suffix_users" by "get_selected_org_suffix_principal_ids"
- Replaced "voc_selected_org_suffix_users" by "voc_selected_org_suffix_userids"
- Added group "gestion_contacts" to give access to duplicated batch action
- Made sure creating_group attribute is set
- Restricted transition "back_to_scanned"
- Corrected "actions_panel_reply" template
- Removed useless IContextAwareDefaultFactory when context is not required
- Corrected task class on old objects
- Constraint to avoid group in group
- Overidded "collective.task.AssignedUsers" voc with "SimplySortedUsers" (value is userid and not username)
- Corrected changeOwnership (scanner to first editor) to avoid fail in getOwner
- Added contraints on fields settings
- Added constraint on settings table value column

3.0.30
------

- Added step "imiodmsmail-remove_om_nplus1_wfadaptation"
- Invalidated "collective.eeafaceted.collectionwidget.cachedcollectionvocabulary" on group un/assignment
- Used "dexterity.localroles.utils.fti_configuration"

3.0 (2021-09-30)
----------------

- Added dmsincoming_email type
  [sgeulette]
- Added classificationFolder and ClassificationCategory types
  [sgeulette]
- Added collective.ckeditortemplates
  [sgeulette]
- Added lecteurs_globaux_cs group
  [sgeulette]
- Added send_modes (attribute, column, criteria)
  [sgeulette]
- Added external reference number criteria in dashboards
  [sgeulette]
- Guarded close and mark_as_sent transitions
  [sgeulette]
- An event sets assigned_user when empty on closing
  [sgeulette]
- Added email signature template
  [sgeulette]
- Can filter on all contacts when filtering
  [sgeulette]
- Set IActionsPanelFolderOnlyAdd on templates and contactlist subfolders
  [sgeulette]
- Replaced to_print adaptation with validated state from n+1 adaptation
  [sgeulette]
- Added close transition to n+ states
  [sgeulette]
- An editor or contributor can delete an appendix file
  [sgeulette]
- A dmsmainfile can't be modified anymore by an editor
  [sgeulette]
- Done full vocabularies for faceted criteria (with deactivated at the end)
  [sgeulette]
- Added replied icon on incoming mail
  [sgeulette]

2.3 (2020-10-08)
----------------

- Made assigned_user_check more precise and improved transition guard
  [sgeulette]

- Added n+ level validation as workflow adaptation
  [sgeulette, bleybaert]

- Added collective.contact.importexport specific pipeline
  [sgeulette]

- Added own groups users management
  [sgeulette]

- Added default value for creating_group
  [sgeulette]

- Added more precise default value for sender on a reply
  [sgeulette]

2.2 (2019-09-12)
----------------

- Added creating_group function feature to enable distinct mail encoders
  [sgeulette]

- Added Lecteurs Globaux CE plone group and local roles.
  [bleybaert]

- Added assigned user selection button
  [sgeulette]

- Added more information when selecting a contact
  [sgeulette]

- Removed actions green bar
  [sgeulette]

- Added due date default value configuration
  [bleybaert]

- Added batch actions buttons (labels, senders, recipients)
  [sgeulette]

- Added subscriber to manage 'lu' label and internal held positions for a new user assignment
  [sgeulette]

- Simplified user and group overview listings
  [sgeulette]

2.1 (2018-08-22)
----------------

- Added mailing features.
  [sgeulette]

- Incoming sender field can contain multiple values
  [sgeulette]

- Added contact lists features.
  [sgeulette]

- Replaced directory view by dashboard view
  [sgeulette]

- Added multiple reply
  [sgeulette]

- Added workflow leading icons for back and again states, in dashboard and item view
  [sgeulette]

- Added viewlet to display when a contact address field is missing
  [sgeulette]

2.0 (2017-06-02)
----------------

- Added outgoing mails models
  [sgeulette]

- Reviewed dmsoutgoingmail schema.
  [sgeulette]

- Added workflow and local roles on dmsoutgoingmail.
  [sgeulette]

- Added im collection: to treat in my group
  [sgeulette]

- Added dashboard on outgoing-mail folder
  [sgeulette]

- Added tasks tab and task behavior
  [sgeulette]

- Manage outgoing mails batch creation
  [sgeulette]

- Protect against user deletion
  [sgeulette]

1.1 (2016-04-14)
----------------

- Extends dmsincomingmail SearchableText with children's scan_id values.
  [sgeulette]

- Added count on "to do" collections
  [sgeulette]

- Added columns: mail_type, sender, task_parent
  [sgeulette]

- Added sender criteria in dashboard
  [sgeulette]

- Managing missing values for mail_type and assigned_user on IImioDmsIncomingMail
  [sgeulette]

- Added batch actions on task dashboard
  [sgeulette]

- Added transition icons
  [sgeulette]

- Added batch action to change recipient groups
  [sgeulette]

- Improvements: disable own delete on contacts, block parent portlets on contacts, add local roles for dir_general
  on contacts, corrected disabled treating_groups bug, updated voc cache, corrected transition batch
  action, added task parent on task view, added method to test user group membership, ordered css
  ordered javascript, improved validation criterion, hide dmsincomingmail creator,
  display again scan information, corrected merging permission problem
  [sgeulette]


1.0 (2016-01-25)
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
