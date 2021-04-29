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

    [TAGS]  RUN1
    Enable autologin as  encodeur
    ${note1}  Add pointy note  id=portal-globalnav  Bandeau des fonctionnalités principales  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    Go to  ${PLONE_URL}/import_scanned?redirect=
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.pretty_link a:first-child  10
    ${note1}  Add pointy note  css=.pretty_link a:first-child  On choisit le courrier entrant sur lequel on veut ajouter une tâche  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    GO to  ${PLONE_URL}/incoming-mail/dmsincomingmail-1
    Sleep  2
    # Sélectionner l'entrée "tâche"
    ${note1}  Add pointy note  css=tr td:nth-child(3)  Ajouter une tâche  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    GO to  ${PLONE_URL}/incoming-mail/dmsincomingmail-1/++add++task
    ${note1}  Add pointy note  css=#form-widgets-title  On ajoute un titre  position=bottom  color=blue
    Sleep  2
    Remove element  id=${note1}
    Input text  id=form-widgets-title  A faire: Tâche très importante
    ${note1}  Add pointy note  css=#form-widgets-ITask-assigned_group  On choisit un service  position=right  color=blue
    Sleep  2
    Remove element  id=${note1}
    Select From List By Index  id=form-widgets-ITask-assigned_group  2
    ${note1}  Add pointy note  css=#form-widgets-ITask-assigned_user  On assigne Fred Agent  position=right  color=blue
    Sleep  2
    Remove element  id=${note1}
    Select From List By Index  id=form-widgets-ITask-assigned_user  1
    ${note1}  Add pointy note  css=#form-buttons-save  On sauvegarde  position=right  color=blue
    Sleep  3
    Remove element  id=${note1}
    Click element  form-buttons-save
    Sleep  2
    ${note1}  Add pointy note  css=.portalMessage.info.success  La tâche a bien été créée  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    GO to  ${PLONE_URL}/
    ${note1}  Add pointy note  id=portaltab-tasks  On vérifie si la tâche est bien assignée à Fred Agent  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    GO to  ${PLONE_URL}/tasks/task-searches
    Wait until element is visible  class=td_cell_assigned_user  20
    ${note1}  Add pointy note  css=.td_cell_assigned_user  Oui, elle lui est bien assignée  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}

    

Utiliser les recherches
# partie guide utilisation : Utiliser les recherches

    # Recherche globale
    [TAGS]  RUN
    Enable autologin as  agent
    Sleep  3
    ${note1}  Add pointy note  id=portal-globalnav  Bandeau des fonctionnalités principales  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    ${note1}  Add pointy note  id=livesearch0  Champ de recherche globale  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    Click element  livesearch0
    Sleep  3
    Input text  name=SearchableText  Recherche globale
    Sleep  3
    Clear Element Text  SearchableText
    GO to  ${PLONE_URL}
    Sleep  1

    # Recherche contextuelle
    Enable autologin as  agent
    Sleep  3
    ${note1}  Add pointy note  id=portal-globalnav  Bandeau des fonctionnalités principales  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    ${note1}  Add pointy note  id=portaltab-incoming-mail  Cliquez sur courrier entrant ou sortant position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    Wait until element is visible  id=portaltab-incoming-mail  20
    GO to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  id=c2  20
    Sleep  3
    ${note1}  Add pointy note  id=c2  Champ de recherche contextuelle  position=bottom  color=blue
    Sleep  3
    Remove element  id=${note1}
    Sleep  3
    Input text  id=c2  Recherche contextuelle
    Sleep  3
    Clear Element Text  id=c2
    Sleep  3
    GO to  ${PLONE_URL}


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
