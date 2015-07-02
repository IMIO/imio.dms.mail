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

Encodage depuis le scanner
# partie 2.3.1 Encodage après envoi par le scanner
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Go to  ${PLONE_URL}/incoming-mail
    Capture and crop page screenshot  doc/utilisation/2-3-1 onglet courrier entrant.png  css=.site-plone  id=portal-footer-wrapper
    
    Capture viewport screenshot  doc/utilisation/test.png

*** Keywords ***
Suite Setup
    Open test browser
    Set Window Size  1024  768
