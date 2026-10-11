*** Settings ***
Documentation  Contacts dashboard: search, person created from the add modal.
Resource  dmsmail_ui.robot
Test Setup  Open the browser
Test Teardown  Close all browsers


*** Test cases ***
Search a contact in the contacts dashboard
    Log in as  encodeur
    Open the dashboard  contacts
    The dashboard result count is  3
    Search in the dashboard  swde
    The dashboard result count is  1
    The dashboard lists  SWDE

Create a person from the contacts dashboard
    Log in as  encodeur
    Open the dashboard  contacts
    Click the dashboard add link  ++add++person
    The modal is open
    ${lastname}=  Modal element  form-widgets-lastname
    Input text  ${lastname}  Leduc
    ${firstname}=  Modal element  form-widgets-firstname
    Input text  ${firstname}  Marc
    Save the modal
    The status message contains  Elément créé
    The title is  Marc Leduc
    Open the dashboard  contacts
    Select the dashboard collection  Toutes les personnes
    The dashboard lists  Marc Leduc
