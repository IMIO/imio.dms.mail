*** Settings ***
Documentation  iA.Docs control panel and navigation.
Resource  dmsmail_ui.robot
Test Setup  Open the browser
Test Teardown  Close all browsers


*** Test cases ***
Change a setting in the iA.Docs control panel
    Log in as  siteadmin  Manager
    Go to  ${PLONE_URL}/@@imiodmsmail-settings
    Wait until element is visible  id=form-widgets-due_date_extension
    Textfield value should be  id=form-widgets-due_date_extension  0
    Input text  id=form-widgets-due_date_extension  5
    Save the form
    The status message contains  Modifications sauvegardées
    Go to  ${PLONE_URL}/@@imiodmsmail-settings
    Textfield value should be  id=form-widgets-due_date_extension  5

The more tab leads to the other sections
    Log in as  encodeur
    Open the dashboard  incoming-mail
    Go to the section of the more tab  Contacts
    The dashboard is loaded
    Location should contain  ${PLONE_URL}/contacts
    The dashboard lists  Electrabel
