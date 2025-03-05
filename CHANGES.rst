Changelog
=========

3.0.60
------

- Last commit at 84828c26b58433d71c2906ad34e9f5b33ab3fe86
- Added various-utils/dv_conv_error to avoid a dv conversion
- Improved dv_conv_error
- Improved redirection
- Added fpaudit integration and configuration
- Updated access document config
- Updated audit templates
- Improved subscriber to avoid error when a user has been deleted
- Hidden audit-log action
- Added audit_contacts group, action to call audit-contacts template and subscriber to made it visible following configuration
- Added get_object_from_relation utils method
- Added IMDGHelper helper view
- Corrected tests
- Added d-im-listing-details.ods template
- Translated templates names
- Improved template
- Improved relations_utils by using batching helpers
- Improved utils.set_dms_config
- Added utils.create_read_label_cron_task to postpone read label updates
- Added utils.cron_read_label_handling method called with cron4plone
- Added test for cron_read_label_handling
- Handled also markers index for IDmsAppendixFile
- Added routing rules table
- Replaced `iemail_manual_forward_transition` setting with `iemail_state_set` rules table
- Allowed module utils. Refactored current_user_groups_ids
- Avoiding error 'Missing.Value' is not iterable
- Limit new-version message to 30 days
- Removed encodeurs roles for dmsoutgoingmail
- Added contact.core update. Persisted cron config
- Added attribute on modified
- Changed default value in routing config
- Corrected migration code
- Handled solr in migration

3.0.59
------

- Last commit at 46f6888adea9602d522d45026d930f3ac9519b7d
- Print old and new version in migration
- Added anchor in minor changes link
- Used defined firefox profile dir if exists
- Corrected bad select2 criteria in robot doc
- Corrected robot test to use a dynamic folder path
- Added email_bcc by default and mandatory in settings
- Removed tree from plus menu when classification is deactivated
- Corrected templates with LO 24.2.5.2
- Better bcc field display
- Added default bcc value depending on config
- Added outgoing email tab in settings to isolate email settings
- Used bcc field to send email
- Used can_delete_batch_files
- Updated dv_clean to include batching functions
- Ordered om states collections as other on created, excepted for scanned state
- Added 3.0.59 migration
- Imported EMPTY values from imio.helpers
- Updated yesno_value index, laterly added to solr
- Added utils method to order settings lists

3.0.58
------

- Last commit at a84d0424f5dcbd0a630268d9e1aec3ba2694ad64
- Corrected menu tab links
- Handled exception when blobstorage is empty
- Do not risk to copy an unfinished template in services
- Blacked files
- Removed useless code
- Displayed creating_group on creation form
- Added test for behavior defaut_creating_group. Used primary organisation if possible
- isorted files

3.0.57
------

- Last commit at 03d33c732c31b69f5d4aa1b4897a5aa2cf2265d2
- Replaced checkbox by multiselect in several faceted widgets
- Added folders state advanced filter
- Import safe_encode from pyutils
- Added treatinggroup-batch-action button on folders

3.0.56
------

- Last commit at 578fbe818ae4636300d1c4b5cb8ed7267bd2c4c1
- Corrected pm url in wsclient configuration settings
- Used objects param because bool(category) is False
- Ordered css and js
- Added sub menu tooltip
- Created plus page and hidden other tabs
- Added content categories examples
- Improved annexes types creation. Removed workflow
- Added possible method to filter document conversion (view used instead)
- Handled types for dv conversion manually
- Moved examples methods from setuphandlers.py to examples.py
- Moved tests to right module
- Improved personnel table
- Reindex possibly bad index
- Avoided json_collections_count view error on annex
- Corrected annex migration
- Added INextPrevNotNavigable to Annex class
- Configured annex actionspanel view
- Do not set documentviewer as defaut view on annex (done dynamically by iconifiedcategory)
- Set different annexes types preview in examples
- Corrected group unassignment bug SUP-34782
- Called cputils_install during migration
- Defined wf chain manually. Reloaded type individually
- Improved migration (removed gs step, added cputils_install if necessary)
- Removed useless messages and added one new (translations)
- Used pm icon for document conversion action
- Added multiple annexes button on classification folder
- Resolved ckeditortemplates error
- Added archived faceted widget
- Added archived color column
- Corrected robot test
- Added group to encodeur example, fixed assigned_user on created OM, fixed and improved tests
- Added examples method to add special model om
- Fixed bug when cleaning examples
- Simplified translation method
- Do not use external edit on annex
- Removed folder rename button
- Checked if treating_groups is defined before reply
- Removed green bar and added actionspanel viewlet on annex
- Disabled not working link on annex file DMS-1005
- Removed z3cform.chosen css
- Improved css to fit left edition column and set fields to column width
- Enlarge to 100% multi select2 field
- Updated video doc
- Corrected search translation
- Improved footer
- Added video guides action, improved translations
- Added INextPrevNotNavigable on several classes
- Added imio.annex overrides.zcml in testing
- Corrected video on document creation
- Corrected behavior zcml definition to avoid warning when Plone starts
- Commented interfaces before real deletion
- Used new basecontent viewlet manager interface
- Updated unconfigure adapter definition after basecontent grok removal
- Corrected migration error
- Adding test for fold's annexes
- Used last pyutils functions
- Replaced entity in assigned user button
- Used batched reindexIndexes

3.0.55
------

- Last commit at 6fb38c82d4c7530c45245be5c994ac3499ba26a0
- Changed dmsommainfile description type
- Folders dashboards: added classification folder types criteria
- Folders dashboards: put classification_tree_identifiers column before title
- Folders dashboards: used separate folder title columns in folders dashboards
- Folders dashboards: removed ModificationDate and review_state columns from folders dashboard
- Folders dashboards: added 'results per page' widget
- Plonegroup behavior: updated to use plonegroup userid behavior
- Plonegroup behavior: updated userid queries. Removed old code
- Plonegroup behavior: removed IDmsPerson
- Plonegroup behavior: updated user link permissions
- Plonegroup behavior: overrided collective.contact.plonegroup.primary_organizations vocabulary
- Plonegroup behavior: used user primary org to set this org first in om treating_groups vocabulary
- Plonegroup behavior: updated relations after interface remove
- Plonegroup behavior: updated held_position userid index if person userid is modified
- Refactored internal persons and held_positions demo creation
- Default values: OM default sender value improvement
- Default values: ensured to reuse already modified values when a form validation occurs
- Default values: Improved assigned user default value
- Included collective.relationhelpers in zcml to access product templates
- Added utils.create_personnel_content to be used in subscribers, steps and migrations
- Replaced get_users() by get_user_from_criteria()
- Improved code for ldap user without email
- Improved tab cont js to avoid error in anonymous
- Loaded ftw.labels js as authenticated
- Removed 30_config_dic
- Added personnel table layout

3.0.54
------

- Last commit at 745394fb5bcc9ea5b4769c3579fc164d4f0fcf71
- Rewriting code

3.0.53
------

- Last commit at a9e047ba2d839bdb821e4d51674f4eb5d6e82e3a
- Rewriting code

3.0.52
------

- Last commit at ecc653949f69cb4e20f8c5c3363ead0eb0755fa5
- Updated robot doc to generate new images
- Set product_version on site creation. Used correct path when running tests

3.0.51
------

- Last commit at ffea0790bdb9e47f7a53b2252473bbfa55fd4dfe
- Display orig_sender_email field when adding a dms incoming email

3.0.50
------

- Last commit at 72a928b41d251e909d8b3100ae72e6e800344667
- Added select_row column on folders tables
- Corrected date data manager when value is None
- Get signed attribute from obj not from brain
- Removed 2.3 upgrade to keep only last one

3.0.49
------

- Last commit at d8112b90dfe8574165b9f2b5abaf38e7464f225a
- Upgraded setup versions and dependency
- Added old_version in new version message

3.0.48
------

- Last commit at ac7f3af67e12d8ffe7560f53f76b4425f9b0b72b
- Be sure archives css is enabled after migration
- Used BaseARUOBatchActionForm for multiple changes batch action
- Used a different vocabulary for old values in batch actions
- Added zope admin delete action
- Added batch actions on folders
- Added min & max for outgoing_date
- Deactivated doc message older than 90 days
- Added version message

3.0.47
------

- Last commit at f24f6283a5d51b202cd8ba8bacf59530979e90b0
- Styled classification_informations to display text as multiline
- Changed documentation urls

3.0.46
------

- Last commit at 412b2e096aa7cebef3416dc59b0f7caf96c1741b
- Added archives.css

3.0.45
------

- Last commit at 4fc248a74e19b1c38a814c1d6f9fa0b9f0eea22f
- Improved `export-users-groups.ods` template
- Replaced check_zope_admin import
- Added invalidate_users_groups method to do special things in tests

3.0.44
------

- Last commit at 35333da3d6a0eddd4de5ceaf2e549e211c923d89
- Added ARCHIVE_SITE variable
- Used OMActiveSenderVocabulary on om sender field, used OMSenderVocabulary with deactivated too to handle missing values
- Added `export-users-groups.ods` template

3.0.43
------

- Last commit at bdf01b89014b2a65f7583333cdab561a57e8884a
- Disabled ftwlabels select2 js
- Do not display assigned user selection message if not needed
- Added cleanRegistries in r part
- A read only field cannot be set by transmogrify.dexterity
- Displayed description as multilines in dms view
- Added Z barcode type to avoid error in scan_id
- Add autolink plugin to ckeditor properties

3.0.40
------

- Last commit at dfeaa9114af48e50baa53f8a854d4b18db5dc2da
- Replaced chosen widget by select2
- Added data_transfer behavior
- Used mail queue to avoid duplicated mails
- Refactored separate_fullname
- Updated solr_config setup with new variables

3.0.39
------

- Last commit at c16d09d9e3306af5cfc8b23c2c2bf0b404851f70
- Improved settings validation
- Modifications for messagesviewlet 1.0
- Filtered templates listing with enabled
- Added labels query fields, voc, criterias and enabled it on om
- Removed accented characters from email string

3.0.38
------

- Last commit at 463b758d8b92e0bfee0df76e505471a40fa98aaa
- Use COMMIT env variable to get commit slice number in migration
- Added clear and sync solr sections in migration
- Overrided solr sync method, so it can be batched
- Disabled solr at migration start and enabled before sync

3.0.37
------

- Last commit at c0c6622e746618543cd9d30e1a393be4f4b7f5e3
- Footer version link goes now to minor versions doc page
- Handled a None reception_date in migration
- Added batch mode in long duration migration methods
- Committed every 1000 items to reduce migration execution time

3.0.36
------

- Last commit at 4eaaa6035ef1d17912c340f5b279ab59ec6f6809
- Updated IMPreManagerValidation wf adaptation to allow back_to_creation
- Avoided error when deleting mails via run-del-mails
- Added receipt document with automated content
- Added correction in migration DMS-902

3.0.35
------

- Last commit at 61ce3816ee6620864955769b41f8d81d3afee325
- Handled better ldap users
- Changed document_in_service widget
- Added saveHasActions in own actionspanel templates

3.0.34
------

- Last commit at 5a2c0b645d5d4565f39ac4b74ec6d1e4b6d95e64
- Added om file class in dv_clean
- Avoided unicodeerror in migration for ldap users
- Made sure a commit will be done for all change in zope ready subscriber
- Used activate info for send_modes from 30_config file
- Corrected migration to add roles only when outgoing emails are activated
- Showed tag version in footer

3.0.33
------

- Last commit at e0bbe5f3278911fdfbcd0219fcce132a25c8d3da
- Replaced xml registry records with new interface schema to avoid overrides of values
- Get week by default if an unknown string has been configured

3.0.32
------

- Last commit at e13d2805af6304076434901a195c7e25fdd06e4a
- Improved code in subcribers to avoid error after using "sharing" tab
- Commented migration code before deletion

3.0.31
------

- Last commit at fe3825eef6f08a7362ac81ef32334a495073abfa
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
- Given local roles on contacts to _editeur group (not only _encodeur)

3.0.30
------

- Added step "imiodmsmail-remove_om_nplus1_wfadaptation"
- Invalidated "collective.eeafaceted.collectionwidget.cachedcollectionvocabulary" on group un/assignment
- Used "dexterity.localroles.utils.fti_configuration"

3.0.29
------

- Added "SendModesBatchActionForm"
- Invalidated "OMActiveSendModesVocabulary" when settings is changed
- Escaped rendered html to avoid xss
- Used in/out mail date to display in contactback references
- Added "various-utils/template_infos" view that gives information on generated document
- Invalidated "OMSenderVocabulary" on group un/assignment
- Used imio_global_cache
- Used "change_user" (logout/login updates correctly roles) and new "siteadmin" user in tests

3.0.28
------

- Remove search overiddes (now done in plonetheme.imioapps)
- Refined permission on "create from template" button

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
- Added receipt document
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
