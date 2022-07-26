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

Plone is installed
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned?redirect=
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Sleep  0.5
    Go to mail  oid=dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10

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
