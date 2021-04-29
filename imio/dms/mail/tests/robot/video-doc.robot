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
${S_S} =  2  # short sleep
${N_S} =  4  # normal sleep
${L_S} =  3  # longer sleep

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
# setup
    [TAGS]  RUN1
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25  additional_address_details=41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID1}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID1}  description  Candidature spontanée  str
    Set field value  ${UID1}  sender  ['${SENDER}']  references
    Set field value  ${UID1}  treating_groups  ${GRH}  str
    Set field value  ${UID1}  assigned_user  agent  str
    Set field value  ${UID1}  original_mail_date  20170314  date
    Fire transition  ${UID1}  propose_to_n_plus_1
    Set field value  ${UID}  title  Votre offre d'emploi d'agent administratif  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  assigned_user  agent  str
    Fire transition  ${UID}  propose_to_n_plus_1
    Enable autologin as  dirg
    Fire transition  ${UID1}  propose_to_agent
    Fire transition  ${UID}  propose_to_agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Select collection  incoming-mail/mail-searches/to_treat
# start video
    pause
# visualisation
    sleep  1
    ${note1}  Add pointy note  css=div.category li:nth-child(3)
    ...  Il faut cliquer sur une recherche, afin d'afficher un tableau de résultats.  position=top  color=blue  width=250
    sleep  ${N_S}
    Remove element  id=${note1}
    ${note1}  Add pointy note  css=table.faceted-table-results td.pretty_link
    ...  On va cliquer sur l'intitulé d'un courrier pour l'ouvrir.  position=top  color=blue
    sleep  ${N_S}
    ${pt1}  Add pointer  css=table.faceted-table-results td.pretty_link
    sleep  1.5
    Remove element  id=${pt1}
    Remove element  id=${note1}

    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail-1
    Wait until element is visible  css=.DV-pageImage  10
    ${note1}  Add pointy note  id=content-core
    ...  Lorsqu'on visualise un courrier, on peut trouver, dans la partie principale de la page, les éléments suivants (en partant de haut en bas).  position=center  color=blue  width=300
    sleep  ${L_S}
    Remove element  id=${note1}

    Highlight  css=table.actionspanel-no-style-table
    ${note1}  Add pointy note  css=table.actionspanel-no-style-table
    ...  Une barre de boutons de gestion. Egalement affichée en bas de page.  position=top  color=blue  width=300
    sleep  ${N_S}
    Clear Highlight  css=table.actionspanel-no-style-table
    Remove element  id=${note1}

    Highlight  id=querynextprev-navigation
    ${note1}  Add pointy note  id=querynextprev-navigation
    ...  Des liens pour passer au courrier précédent/suivant de la recherche en cours.  position=left  color=blue  width=300
    sleep  ${N_S}
    Clear Highlight  id=querynextprev-navigation
    Remove element  id=${note1}

    Highlight  css=h1 span.pretty_link_content
    ${note1}  Add pointy note  css=h1 span.pretty_link_content
    ...  L’intitulé du courrier, commençant par son numéro de référence interne.  position=top  color=blue  width=300
    sleep  ${N_S}
    Clear Highlight  css=h1 span.pretty_link_content
    Remove element  id=${note1}

    Highlight  id=plone-document-byline
    ${note1}  Add pointy note  id=plone-document-byline
    ...  Une ligne d’information indiquant la date de dernière modification, ainsi qu’un lien vers l’historique (coloré en rouge quand une note s’y trouve).  position=top  color=blue  width=300
    sleep  ${N_S}
    Clear Highlight  id=plone-document-byline
    Remove element  id=${note1}

    Highlight  css=div.viewlet_workflowstate
    ${note1}  Add pointy note  css=div.viewlet_workflowstate
    ...  L’état de l’élément sur un fond de couleur spécifique.  position=left  color=blue  width=300
    sleep  ${L_S}
    Clear Highlight  css=div.viewlet_workflowstate
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=#labeling-viewlet ul
    ...  Des boutons permettant d’associer un libellé: « lu » (pour les courriers en copie), « suivi » (pour suivre des courriers).  position=left  color=blue  width=200
    sleep  ${L_S}
    Remove element  id=${note1}

    Highlight  id=parent-fieldname-description
    ${note1}  Add pointy note  id=parent-fieldname-description
    ...  La description plus complète du courrier (s'il y en a une).  position=left  color=blue  width=200
    sleep  ${N_S}
    Clear Highlight  id=parent-fieldname-description
    Remove element  id=${note1}

    Highlight  id=fields
    ${note1}  Add pointy note  id=fields
    ...  Les champs du courrier: ce sont les informations encodées dans la fiche.  position=top  color=blue  width=300
    sleep  ${N_S}
    Clear Highlight  id=fields
    Remove element  id=${note1}

    Highlight  id=fieldset-versions
    ${note1}  Add pointy note  id=fieldset-versions
    ...  La prévisualisation du ficher ged (fichier principal).  position=top  color=blue  width=300
    sleep  ${N_S}
    Clear Highlight  id=fieldset-versions
    Remove element  id=${note1}

#    ${note1}  Add pointy note  css=#fieldset-versions table.listing td:nth-child(1)
#    ...  Cette icône permet de télécharger le fichier ged au format pdf.  position=top  color=blue  width=300
#    sleep  ${N_S}
#    Remove element  id=${note1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(1)
    ...  On peut cliquer sur cette icône pour modifier les données de la fiche.  position=top  color=blue  width=300
    sleep  ${N_S}
    ${pointer1}  Add pointer  css=table.actionspanel-no-style-table td:nth-child(1)
    sleep  1.5
    Remove element  id=${pointer1}
    Remove element  id=${note1}

# modification
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail-1/edit
    Wait until element is visible  css=.DV-pageImage  10

#    ${note1}  Add pointy note  id=content-core
#    ...  Lorsqu'on modifie un courrier, on peut changer certains champs de la fiche.  position=center  color=blue  width=300
#    sleep  ${L_S}
#    Remove element  id=${note1}

    ${note1}  Add pointy note  id=formfield-form-widgets-IDublinCore-description
    ...  Parfois, certains champs ne sont pas modifiables: tout dépend de votre rôle et de l'état de l'élément. C'est le cas ici du titre, de la description, des expéditeurs, etc.  position=right  color=blue  width=400
    sleep  8
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=formfield-form-widgets-ITask-assigned_user
    ...  On peut reprendre le travail d'un autre, au besoin.  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=formfield-form-widgets-recipient_groups
    ...  On peut ajouter des services en copie.  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=formfield-form-widgets-ITask-due_date
    ...  On peut mettre une échéance pour pouvoir trier les courriers dans les tableaux de bord.  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=formfield-form-widgets-reply_to
    ...  On peut ajouter des courriers liés à cette fiche, en cherchant sur une référence interne ou un mot du titre.  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ScrollDown

    ${note1}  Add pointy note  id=formfield-form-widgets-ITask-task_description
    ...  On peut laisser des notes dans cette zone (le chef de service, l'agent traitant).  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=formfield-form-widgets-external_reference_no
    ...  On peut ajouter la référence de l'expéditeur qui servira lors d'une réponse.  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=form-buttons-cancel
    ...  Il faut sauvegarder (si modifications) ou annuler pour sortir du mode « édition ».  position=right  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

# changement état

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
#    Set Window Size  1200  1920
#    Set Window Size  1260  2880
#    Set Window Size  1280  720
    Set Window Size  1400  1050
    Set Suite Variable  ${CROP_MARGIN}  5
    Set Selenium Implicit Wait  2
    Set Selenium Speed  0.2
    Enable autologin as  Manager
    Set autologin username  dirg
    Go to  ${PLONE_URL}/robot_init
    Disable autologin
