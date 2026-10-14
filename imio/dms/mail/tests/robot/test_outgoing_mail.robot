*** Settings ***
Documentation  Outgoing mails: add form, document created from a template.
Resource  dmsmail_ui.robot
Test Setup  Open the browser
Test Teardown  Close all browsers


*** Test cases ***
Create an outgoing mail with the add form
    Log in as  agent
    Open the dashboard  outgoing-mail
    The dashboard result count is  6
    Click the dashboard add link  ++add++dmsoutgoingmail
    Wait until element is visible  id=form-widgets-IDublinCore-title
    The field contains  sender  Fred Agent
    Input text  id=form-widgets-IDublinCore-title  Réfection des trottoirs
    Select in the autocomplete widget  recipients  electrabel  Electrabel
    Select checkbox  id=form-widgets-send_modes-0
    Save the form
    The title is  Réfection des trottoirs
    The field contains  recipients  Electrabel
    The field contains  sender  Fred Agent
    The workflow state is  En création
    Open the dashboard  outgoing-mail
    The dashboard result count is  7

Create the document of an outgoing mail from a template
    Log in as  agent
    Go to the mail  reponse2  dmsoutgoingmail
    Click the panel button  create-from-template
    The modal is open
    Choose the template in the modal  Modèle de base
    # the testing layer disables the redirection after the generation: the browser stays on a blank page
    Wait until location contains  persistent-document-generation
    Go to the mail  reponse2  dmsoutgoingmail
    The mail files list  Modèle de base
