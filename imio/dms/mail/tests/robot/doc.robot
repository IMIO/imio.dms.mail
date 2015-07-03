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
    Wait until element is visible  css=.DV-pageImage  5
    Capture and crop page screenshot  doc/utilisation/2-3-1 lien modifier courrier.png  id=contentview-edit  id=content-history  css=table.actionspanel-no-style-table
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/edit
    Wait until element is visible  css=.DV-pageImage  5
    Capture and crop page screenshot  doc/utilisation/2-3-1 édition courrier.png  css=.site-plone  id=portal-footer-wrapper
    Click element  css=.DV-textView span.DV-trigger
    Highlight  css=.DV-textView
    ${note1}  Add pointy note  css=.DV-textView  Onglet texte  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-1 édition texte océrisé.png  id=portal-columns  ${note1}
    Clear highlight  css=.DV-textView
    Input text  name=form.widgets.IDublinCore.title  Candidature à un poste
    Input text  name=form.widgets.IDublinCore.description  Lettre de candidature spontanée
    Input text  name=form.widgets.sender.widgets.query  le
    Wait until element is visible  css=.ac_results  5
    Capture and crop page screenshot  doc/utilisation/2-3-1 expéditeur recherche le.png  id=fieldset-default
    Capture viewport screenshot  doc/utilisation/test.png

*** Keywords ***
Suite Setup
    Open test browser
    Set Window Size  1024  768
