*** Settings ***
Resource  plone/app/robotframework/keywords.robot
Resource  plone/app/robotframework/selenium.robot

Library  Remote  ${PLONE_URL}/RobotRemote
Library  plone.app.robotframework.keywords.Debugging
Library  Selenium2Screenshots

Suite Setup  Suite Setup
Suite Teardown  Close all browsers

*** Test cases ***

Utilisateur
# partie 2.1 Premiers pas
    Go to  ${PLONE_URL}
    Capture and crop page screenshot  doc/utilisation/2-1 accès à l'application.png  css=.site-plone  id=portal-footer-wrapper
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}
    Capture and crop page screenshot  doc/utilisation/2-1 page d'accueil.png  css=.site-plone  id=portal-footer-wrapper
    Capture and crop page screenshot  doc/utilisation/2-1 fil d'ariane.png  id=breadcrumbs-you-are-here  id=breadcrumbs-home
# partie 2.2 Visualisation des éléments
    Go to  ${PLONE_URL}/incoming-mail
    Capture and crop page screenshot  doc/utilisation/2-2 onglet courrier entrant.png  css=.site-plone  id=portal-footer-wrapper
    Go to  ${PLONE_URL}/incoming-mail/courrier3
    Wait until element is visible  css=.DV-pageImage  5
    Capture and crop page screenshot  doc/utilisation/2-2 courrier entrant.png  css=.site-plone  id=portal-footer-wrapper

Encodage depuis le scanner
# partie 2.3.1 Encodage après envoi par le scanner
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Go to  ${PLONE_URL}/incoming-mail
    Capture and crop page screenshot  doc/utilisation/2-3-1 onglet courrier entrant.png  css=.site-plone  id=portal-footer-wrapper
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/@@plone_lock_operations/create_lock
    Go to  ${PLONE_URL}/incoming-mail/collections/searchfor_created
    Capture and crop page screenshot  doc/utilisation/2-3-1 recherche en création.png  css=.site-plone  id=portal-footer-wrapper
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/@@plone_lock_operations/safe_unlock
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-1 lien modifier courrier.png  id=contentview-edit  id=content-history  css=table.actionspanel-no-style-table
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/edit
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-1 édition courrier.png  css=.site-plone  id=portal-footer-wrapper
    Click element  css=.DV-textView span.DV-trigger
    Highlight  css=.DV-textView
    ${note1}  Add pointy note  css=.DV-textView  Onglet texte  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-1 édition texte océrisé.png  id=portal-columns  ${note1}
    Clear highlight  css=.DV-textView
    Remove element  id=${note1}
    Input text  name=form.widgets.IDublinCore.title  Candidature à un poste d'ouvrier communal
    Input text  name=form.widgets.IDublinCore.description  Lettre de candidature spontanée
    Input text  name=form.widgets.sender.widgets.query  le
    Wait until element is visible  css=.ac_results  10
    Capture and crop page screenshot  doc/utilisation/2-3-1 expéditeur recherche le.png  id=fieldset-default
    Click element  id=form-widgets-notes
    Wait until element is not visible  css=.ac_results  10
    Input text  name=form.widgets.sender.widgets.query  leduc
    ${note2}  Add pointy note  css=.addnew  Lien nouveau contact  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-1 expéditeur recherche leduc.png  id=fieldset-default
    Remove element  id=${note2}
    Click element  css=.addnew
    Wait until element is visible  css=.overlay-contact-addnew
    Sleep  2
    Capture and crop page screenshot  doc/utilisation/2-3-1 expéditeur création.png  css=.overlay-contact-addnew
    Input text  name=oform.widgets.organization.widgets.query  IMIO
    Wait until element is visible  css=#oform-widgets-organization-autocomplete .addnew
    ${note3}  Add pointy note  css=#oform-widgets-organization-autocomplete .addnew  Lien nouvelle organisation  position=right  color=blue
    Highlight  css=#oform-widgets-organization-autocomplete .addnew
    Capture and crop page screenshot  doc/utilisation/2-3-1 expéditeur création lien organisation.png  css=.overlay-contact-addnew  ${note3}
    Remove element  id=${note3}
    Clear highlight  css=#oform-widgets-organization-autocomplete .addnew
    Click element  css=#oform-widgets-organization-autocomplete .addnew
    Wait until element is visible  id=pb_2  10
    Update element style  id=formfield-form-widgets-activity  display  none
    Capture and crop page screenshot  doc/utilisation/2-3-1 expéditeur création organisation.png  id=pb_2
    
    Capture viewport screenshot  doc/utilisation/test.png

*** Keywords ***
Suite Setup
    Open test browser
#    Set Window Size  1024  768
    Set Window Size  1280  800
