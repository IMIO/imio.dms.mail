*** Settings ***
Resource  plone/app/robotframework/keywords.robot
Resource  plone/app/robotframework/selenium.robot
Resource  common.robot

Library  Remote  ${PLONE_URL}/RobotRemote
Library  Selenium2Screenshots

Suite Setup  Suite Setup
Suite Teardown  Close all browsers

*** Variables ***

#${BROWSER} =  GoogleChrome
${SELENIUM_RUN_ON_FAILURE} =  Debug

*** Test Cases ***

Naviguer
# partie guide utilisation : naviguer dans l'interface
    [TAGS]  RUN
    Enable autologin as  agent
    ${note1}  Add pointy note  id=portaltab-tasks  Bandeau principal des fonctionnalités  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    ${note1}  Add pointy note  id=portaltab-incoming-mail  Cliquer pour rentrer dans le courrier entrant  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    Go to  ${PLONE_URL}/incoming-mail
    ${note1}  Add pointy note  css=.portlet.portletWidgetCollection  Tableaux de bords  position=right  color=blue
    Sleep  3
    Remove element  id=${note1}
    Pause

Traiter un courrier
# partie guide utilisation : traiter un courrier


Répondre à un courrier
# partie guide utilisation : Répondre à un courrier


Créer un courrier sortant
# partie guide utilisation : Créer un courrier sortant


Créer un courrier bureautique
# partie guide utilisation : Créer un courrier bureautique


Transférer un email
# partie guide utilisation : Transférer un email


Valider un courrier entrant
# partie guide utilisation : Valider un courrier entrant


Ajouter un contact
# partie guide utilisation : Ajouter un contact


Ajouter une annexe
# partie guide utilisation : Ajouter une annexe


Ajouter une tâche
# partie guide utilisation : Ajouter une tâche


Utiliser les recherches
# partie guide utilisation : Utiliser les recherches


Gérer les modèles
# partie guide utilisation : Gérer les modèles


CS nouveau
# partie 2.3.2 Nouveau courrier sortant
    [TAGS]  RUN
    Enable autologin as  agent
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  css=.table_faceted_no_results  10

    ### Create outgoingmail
    Pause
    ${note1}  Add pointy note  id=newOMCreation  Créer un nouveau courrier  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-2-cs-1-lien-ajout.png  id=portal-column-one  ${note1}
    Sleep  3
    Remove element  id=${note1}
    Click element  newOMCreation
    Wait until element is visible  css=.template-dmsoutgoingmail #formfield-form-widgets-sender  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-3-2-cs-1-creation.png  id=content
    Input text  name=form.widgets.IDublinCore.title  Annonce de la réfection des trottoirs Rue Moyenne
    ${note1}  Add pointy note  id=form-widgets-IDublinCore-title  Encoder l'objet du courrier  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    Input text  name=form.widgets.recipients.widgets.query  Non encod
    ${note1}  Add pointy note  id=form-widgets-recipients-widgets-query  Rechercher le contact dans l'annuaire et le sélectionner  position=top  color=blue
    Sleep  3
    Remove element  id=${note1}
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    Click element  css=.ac_results:not([style*="display: none"]) li
    Click button  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Capture and crop page screenshot  doc/utilisation/2-3-2-cs-1-creation-finie.png  css=table.actionspanel-no-style-table  css=div.viewlet_workflowstate  id=formfield-form-widgets-internal_reference_no
    ${note1}  Add pointy note  css=.apButtonAction_create-from-template  Générer le courrier à partir d'un modèle  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-moyenne/create_main_file?filename=Refection+trottoir.odt&title=Réfection+trottoir&mainfile_type=dmsommainfile
    Sleep  2
    Wait until element is visible  css=.DV-pageImage  10
    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-moyenne
    Sleep  2
    Wait until element is visible  css=.DV-pageImage  10
    ${note1}  Add pointy note  id=fieldset-versions  Le courrier généré apparait sur la droite  position=top  color=blue
    Sleep  3
    Remove element  id=${note1}
    Capture and crop page screenshot  doc/utilisation/2-3-2-cs-2-visualisation.png  css=table.actionspanel-no-style-table  id=fieldset-versions
    Pause

*** Keywords ***
Suite Setup
    Open test browser
#    Set Window Size  1024  768
#    Set Window Size  1200  1920
#    Set Window Size  1260  2880
    Set Window Size  1280  720
    Set Suite Variable  ${CROP_MARGIN}  5
    Set Selenium Implicit Wait  2
    Set Selenium Speed  0.2
    Enable autologin as  Manager
    Set autologin username  dirg
    Go to  ${PLONE_URL}/robot_init
    Disable autologin
