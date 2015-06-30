*** Settings ***
Resource  plone/app/robotframework/keywords.robot
Resource  plone/app/robotframework/selenium.robot

Library  Remote  ${PLONE_URL}/RobotRemote
Library  plone.app.robotframework.keywords.Debugging

Suite Setup  Suite Setup
Suite Teardown  Close all browsers

Test Setup  Test Setup

*** Test cases ***

Plone is installed
    Go to  ${PLONE_URL}/incoming-mail
    Page should contain  Réalisé avec Plone

*** Keywords ***
Suite Setup
    Open test browser
    Enable autologin as  Manager

Test Setup
    ${test1_uid}=  Create content  type=dmsincomingmail  id=test1  title=Test 1  container=plone/incoming-mail
    Create content  type=dmsmainfile  id=file1  title=  container=${test1_uid}
