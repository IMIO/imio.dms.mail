*** Settings ***
Resource  plone/app/robotframework/keywords.robot
Resource  plone/app/robotframework/selenium.robot
Resource  common.robot

Library  Remote  ${PLONE_URL}/RobotRemote
Library  Selenium2Screenshots

Suite Setup  Suite Setup
Suite Teardown  Close all browsers

#Test Setup  Test Setup

*** Variables ***

#${BROWSER} =  GoogleChrome
${SELENIUM_RUN_ON_FAILURE} =  Debug

*** Test cases ***

OM default values on new OM
    [TAGS]  RUN01
    ### Create outgoingmail as encodeur
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  css=.table_faceted_no_results  10
    Click element  newOMCreation
    Wait until element is visible  css=.template-dmsoutgoingmail #formfield-form-widgets-sender  10
    Sleep  0.5
    List selection should be  form-widgets-treating_groups  Direction générale
    List selection should be  form-widgets-ITask-assigned_user  Michel Chef
    ${HP} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/encodeur/encodeur-secretariat
    ${ORG} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/secretariat
    List selection should be  form_widgets_sender  ${HP}_${ORG}_encodeur
    Disable autologin
    ### Create outgoingmail as agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  css=.table_faceted_no_results  10
    Click element  newOMCreation
    Wait until element is visible  css=.template-dmsoutgoingmail #formfield-form-widgets-sender  10
    Sleep  0.5
    List selection should be  form-widgets-treating_groups  Direction générale - Communication
    List selection should be  form-widgets-ITask-assigned_user  Fred Agent
    ${HP} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/agent/agent-communication
    ${ORG} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/communication
    List selection should be  form_widgets_sender  ${HP}_${ORG}_agent
    Disable autologin
    ### Create outgoingmail as chef
    Enable autologin as  chef
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  css=.table_faceted_no_results  10
    Click element  newOMCreation
    Wait until element is visible  css=.template-dmsoutgoingmail #formfield-form-widgets-sender  10
    Sleep  0.5
    List selection should be  form-widgets-treating_groups  Direction générale
    List selection should be  form-widgets-ITask-assigned_user  Michel Chef
    ${HP} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/chef/responsable-direction-generale
    ${ORG} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale
    List selection should be  form_widgets_sender  ${HP}_${ORG}_chef
    Disable autologin
    ### Create outgoingmail as agent1
    Enable autologin as  agent1
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  css=.table_faceted_no_results  10
    Click element  newOMCreation
    Wait until element is visible  css=.template-dmsoutgoingmail #formfield-form-widgets-sender  10
    Sleep  0.5
    List selection should be  form-widgets-treating_groups  Événements
    List selection should be  form-widgets-ITask-assigned_user  Stef Agent
    ${HP} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/agent1/agent-evenements
    ${ORG} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/evenements
    List selection should be  form_widgets_sender  ${HP}_${ORG}_agent1
    Disable autologin

OM default values on response
    [TAGS]  RUN02
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    # set treating_groups value to enable transition
    ${im_path} =  Get mail path  oid=dmsincomingmail
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${im_path}
    ${SECR} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/secretariat
    ${EVE} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/evenements
    ${SENDER} =  Path to uid  /${PLONE_SITE_ID}/contacts/electrabel
    Set field value  ${UID}  title  Candidature  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  treating_groups  ${SECR}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  recipient_groups  ['${EVE}']  list
    Fire transition  ${UID}  propose_to_n_plus_1
    Enable autologin as  dirg
    Fire transition  ${UID}  propose_to_agent
    # Respond as encodeur
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Click button  css=#viewlet-above-content-title .apButtonAction_reply
    Wait until element is visible  css=.template-reply #formfield-form-widgets-ITask-due_date  10
    Sleep  1
    List selection should be  form-widgets-treating_groups  Direction générale - Secrétariat
    List selection should be  form-widgets-ITask-assigned_user  Jean Encodeur
    ${HP} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/encodeur/encodeur-secretariat
    ${ORG} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/secretariat
    List selection should be  form_widgets_sender  ${HP}_${ORG}_encodeur
    Disable autologin
    # Respond as agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Click button  css=#viewlet-above-content-title .apButtonAction_reply
    Wait until element is visible  css=.template-reply #formfield-form-widgets-ITask-due_date  10
    Sleep  1
    List selection should be  form-widgets-treating_groups  Direction générale - Secrétariat
    List selection should be  form-widgets-ITask-assigned_user  Fred Agent
    ${HP} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/agent/agent-secretariat
    ${ORG} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/secretariat
    List selection should be  form_widgets_sender  ${HP}_${ORG}_agent
    Disable autologin
    # Respond as chef
    Enable autologin as  chef
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Click button  css=#viewlet-above-content-title .apButtonAction_reply
    Wait until element is visible  css=.template-reply #formfield-form-widgets-ITask-due_date  10
    Sleep  1
    List selection should be  form-widgets-treating_groups  Direction générale - Secrétariat
    List selection should be  form-widgets-ITask-assigned_user  Michel Chef
    ${HP} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/chef/responsable-secretariat
    ${ORG} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/secretariat
    List selection should be  form_widgets_sender  ${HP}_${ORG}_chef
    Disable autologin
    # Respond as agent1
    Enable autologin as  agent1
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Click button  css=#viewlet-above-content-title .apButtonAction_reply
    Wait until element is visible  css=.template-reply #formfield-form-widgets-ITask-due_date  10
    Sleep  1
    List selection should be  form-widgets-treating_groups  Événements
    List selection should be  form-widgets-ITask-assigned_user  Stef Agent
    ${HP} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/agent1/agent-evenements
    ${ORG} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/evenements
    List selection should be  form_widgets_sender  ${HP}_${ORG}_agent1
    Disable autologin

*** Keywords ***
Suite Setup
    Open test browser
    # Set Window Size  1080  1920
    # Set Window Size  1260  2880
    # Set Window Size  1260  2240
    Set Window Size  1200  1920
    Set Suite Variable  ${CROP_MARGIN}  5
    Set Selenium Implicit Wait  2
    Set Selenium Speed  0.2
    Enable autologin as  Manager
    Set autologin username  dirg
    Go to  ${PLONE_URL}/robot_init
    Disable autologin

Test Setup
    bad path
    ${test1_uid}=  Create content  type=dmsincomingmail  id=test1  title=Test 1  container=plone/incoming-mail
    Create content  type=dmsmainfile  id=file1  title=  container=${test1_uid}
