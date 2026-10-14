*** Settings ***
Documentation  Incoming mails: dashboard, add form, actions panel (transition, reply, task, annexes).
Resource  dmsmail_ui.robot
Test Setup  Open the browser
Test Teardown  Close all browsers


*** Test cases ***
The incoming mail dashboard lists the mails
    Log in as  encodeur
    Open the dashboard  incoming-mail
    The dashboard result count is  9
    The dashboard lists  E0001 - Courrier 1
    The dashboard row contains  E0001 - Courrier 1  Electrabel
    The dashboard collection count is  État: en création  9

A dashboard collection filters the mails
    Log in as  encodeur
    Fire the mail transition  courrier1  propose_to_manager
    Open the dashboard  incoming-mail
    The dashboard collection count is  État: en création  8
    Select the dashboard collection  État: à valider par le DG
    The dashboard result count is  1
    The dashboard lists  E0001 - Courrier 1
    Select the dashboard collection  État: à traiter
    The dashboard result count is  0

Create an incoming mail with the add form
    Log in as  encodeur
    Open the dashboard  incoming-mail
    Click the dashboard add link  ++add++dmsincomingmail
    Wait until element is visible  id=form-widgets-IDublinCore-title
    Input text  id=form-widgets-IDublinCore-title  Braderie annuelle
    Select in the autocomplete widget  sender  swde  SWDE
    Select from list by label  id=form-widgets-treating_groups  Direction technique
    Select from list by value  id=form-widgets-mail_type  courrier
    Save the form
    The title is  Braderie annuelle
    The field contains  sender  SWDE
    The field contains  treating_groups  Direction technique
    The workflow state is  En création
    Open the dashboard  incoming-mail
    The dashboard result count is  10

Propose an incoming mail to the DG from the actions panel
    Log in as  encodeur
    Go to the mail  courrier1
    The workflow state is  En création
    Click the panel button  propose_to_manager
    The status message contains  L'état de l'élément a changé.
    The workflow state is  À valider par le DG

Reply to an incoming mail
    Log in as  encodeur
    Go to the mail  courrier1
    Click the panel button  reply
    Wait until element is visible  id=form-widgets-IDublinCore-title
    Textfield value should be  id=form-widgets-IDublinCore-title  Réponse: Courrier 1
    The field contains  recipients  Electrabel
    The field contains  reply_to  E0001 - Courrier 1
    Save the form
    The title is  Réponse: Courrier 1
    The field contains  recipients  Electrabel
    The field contains  reply_to  E0001 - Courrier 1
    The workflow state is  En création

Add a task to an incoming mail
    Log in as  encodeur
    Go to the mail  courrier2
    Add from the panel menu  Tâche
    Wait until element is visible  id=form-widgets-title
    Input text  id=form-widgets-title  Vérifier la demande
    Save the form
    The status message contains  Elément créé
    The title is  Vérifier la demande
    Page should contain  E0002 - Courrier 2
    Go to the mail  courrier2
    Wait until page contains  Vérifier la demande

Add an annex with the multiple annexes modal
    Log in as  encodeur
    Go to the mail  courrier1
    Click the panel button  annexes
    The modal is open
    Upload in the annexes modal  ${CURDIR}/annexe.pdf
    Go to the mail  courrier1
    The mail files list  annexe
