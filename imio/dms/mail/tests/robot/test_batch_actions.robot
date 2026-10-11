*** Settings ***
Documentation  Dashboard batch actions on the selected mails.
Resource  dmsmail_ui.robot
Test Setup  Open the browser
Test Teardown  Close all browsers


*** Test cases ***
Change the treating group of the selected mails
    Log in as  encodeur
    Open the dashboard  incoming-mail
    The dashboard row contains  E0001 - Courrier 1  Direction générale
    Select the dashboard rows  E0001 - Courrier 1  E0002 - Courrier 2
    Click the batch action  treatinggroup
    Page should contain  2 élément(s)
    ${select}=  Modal element  form-widgets-treating_group
    Select from list by label  ${select}  Direction technique - Voiries
    Apply the modal
    The modal is closed
    The dashboard is loaded
    The dashboard row contains  E0001 - Courrier 1  Direction technique - Voiries
    The dashboard row contains  E0002 - Courrier 2  Direction technique - Voiries
    The dashboard row contains  E0003 - Courrier 3  Direction générale - GRH
