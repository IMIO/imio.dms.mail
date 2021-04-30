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
${L_S} =  6  # longer sleep
${W_WIDTH} =  1680  # width 1200 1260 1280
${W_HEIGHT} =  1050  # height 1920 2880 720

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
# setup
    [TAGS]  RUN1
    Enable autologin as  encodeur
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Go to  ${PLONE_URL}/import_scanned
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25  additional_address_details=41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  description  Candidature spontanée  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  original_mail_date  20170314  date
    Fire transition  ${UID}  propose_to_n_plus_1
    Set field value  ${UID1}  title  Votre offre d'emploi d'agent administratif  str
    Set field value  ${UID1}  sender  ['${SENDER}']  references
    Set field value  ${UID1}  treating_groups  ${GRH}  str
    Set field value  ${UID1}  assigned_user  agent  str
    Fire transition  ${UID1}  propose_to_n_plus_1
    Enable autologin as  dirg
    Fire transition  ${UID}  propose_to_agent
    Fire transition  ${UID1}  propose_to_agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Select collection  incoming-mail/mail-searches/to_treat
# start video
    pause
# visualisation
    ${main1}  Add title  Tutoriel vidéo iA.docs : comment traiter un courrier entrant...
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=div.category li:nth-child(3)
    ...  Il faut cliquer sur une recherche, afin d'afficher un tableau de résultats.  position=top  color=blue  width=250
    sleep  ${N_S}
    Remove element  id=${note1}
    ${note1}  Add pointy note  css=#faceted_table tr:nth-child(2) td.pretty_link
    ...  On va cliquer sur l'intitulé d'un courrier pour l'ouvrir.  position=top  color=blue
    sleep  ${N_S}
    Add clic  css=#faceted_table tr:nth-child(2) td.pretty_link
    Remove element  id=${note1}

    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10
    ${main1}  Add main note  Lorsqu'on visualise un courrier, on peut trouver, dans la partie principale de la page, les éléments suivants (en partant de haut en bas).
    sleep  ${L_S}
    Remove element  id=${main1}

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
    ...  Une ligne d’information indiquant la date de dernière modification, ainsi qu’un lien vers l’historique.  position=top  color=blue  width=300
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
    Add clic  css=table.actionspanel-no-style-table td:nth-child(1)
    Remove element  id=${note1}

# modification
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/edit
    Wait until element is visible  css=.DV-pageImage  10

#    ${main1}  Add main note  Lorsqu'on modifie un courrier, on peut changer certains champs de la fiche.
#    sleep  ${L_S}
#    Remove element  id=${main1}

    ${main1}  Add main note  Parfois, certains champs ne sont pas modifiables: tout dépend de votre rôle et de l'état de l'élément. C'est le cas ici du titre, de la description, des expéditeurs, etc.
    sleep  8
    Remove element  id=${main1}

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
    ...  Il faut sauvegarder (si des modifications ont été apportées) ou annuler pour sortir du mode « édition ».  position=right  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=form-buttons-cancel
    Click element  id=form-buttons-cancel

# changement état
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10

    ${main1}  Add main note  Le cycle de vie d’un élément (courrier, tâche) est constitué de différents états par lesquels l’élément transite depuis sa création, jusqu’à sa clôture.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Les états d'un courrier entrant sont par exemple: « En création », « À valider par le N+1 », « À traiter », « En traitement » et « Clôturé ».
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=div.faceted-tagscloud-collection-widget-portlet li:nth-child(12)
    ...  Les états visibles par l'utilisateur sont montrés dans les recherches commençant par "État".  position=top  color=blue  width=250
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=div.viewlet_workflowstate
    ...  L'état actuel est affiché avec sa couleur.  position=left  color=blue  width=250
    sleep  ${N_S}
    Remove element  id=${note1}

    ${main1}  Add main note  Les droits de l'utilisateur varient d'un état à l'autre. Par exemple, un agent ne pourra plus modifier un courrier quand il est dans l'état « Clôturé ».
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Une transition sert à changer d'état. Elle peut être effectuée suivant les droits de l'utilisateur et des conditions spécifiques.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(3)
    ...  Les boutons en bleu permettent d'effectuer une transition.  position=top  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(3)
    Remove element  id=${note1}

    Fire transition  ${UID}  treat
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10

    ${note1}  Add pointy note  css=div.viewlet_workflowstate
    ...  L'état a changé.  position=left  color=blue
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(2)
    ...  Ainsi que les transitions possibles. On peut revenir en arrière.  position=top  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(2)
    Remove element  id=${note1}
    Click element  css=table.actionspanel-no-style-table td:nth-child(2)
    Wait until element is visible  css=#confirmTransitionForm

    ${note1}  Add pointy note  css=#confirmTransitionForm
    ...  Quand on revient en arrière, on peut laisser un commentaire.  position=left  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Input text  name=comment  Je vais et je viens...
    Sleep  ${S_S}
    Click element  css=#confirmTransitionForm input:nth-child(1)
    Wait until element is visible  css=.DV-pageImage  10

    ${note1}  Add pointy note  css=#parent-fieldname-title span.pretty_link_icons img:nth-child(1)
    ...  Une icône spécifique indique ce retour en arrière.  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=#content-history a
    ...  L'historique s'affiche en rouge quand il y a un commentaire. On peut cliquer pour le consulter.  position=top  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=#content-history a
    Remove element  id=${note1}

    Click element  css=#content-history a
    Wait until element is visible  css=div.overlay-history

#    ${note1}  Add pointy note  css=div.overlay-history
#    ...  On peut consulter l'historique de l'élément...  position=bottom  color=blue  width=300
#    sleep  ${L_S}
#    Remove element  id=${note1}
    Add clic  css=div.overlay-history div.close
    Click element  css=div.overlay-history div.close

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(3)
    ...  Si on clique à nouveau sur « Traiter ».  position=top  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(3)
    Remove element  id=${note1}
    Click element  css=table.actionspanel-no-style-table td:nth-child(3)
    Wait until element is visible  css=.DV-pageImage  10

    ${note1}  Add pointy note  css=#parent-fieldname-title span.pretty_link_icons img:nth-child(1)
    ...  Une icône spécifique indique qu'on revient à un état déjà rencontré.  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    Add title  Ce tutoriel vidéo est fini ;-)
    sleep  ${L_S}

Répondre à un courrier
# setup
    [TAGS]  RUN1
    Enable autologin as  encodeur
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Go to  ${PLONE_URL}/import_scanned
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25  additional_address_details=41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  description  Candidature spontanée  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  original_mail_date  20170314  date
    Fire transition  ${UID}  propose_to_n_plus_1
    Set field value  ${UID1}  title  Votre offre d'emploi d'agent administratif  str
    Set field value  ${UID1}  sender  ['${SENDER}']  references
    Set field value  ${UID1}  treating_groups  ${GRH}  str
    Set field value  ${UID1}  assigned_user  agent  str
    Fire transition  ${UID1}  propose_to_n_plus_1
    Enable autologin as  dirg
    Fire transition  ${UID}  propose_to_agent
    Fire transition  ${UID1}  propose_to_agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Select collection  incoming-mail/mail-searches/to_treat

    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10

# start video
#    pause
# visualisation répondre

    ${main1}  Add title  Tutoriel vidéo iA.docs : comment répondre à un courrier entrant...
    sleep  ${L_S}
    Remove element  id=${main1}

    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10
    ${main1}  Add main note  Lorsqu'on visualise un courrier, on peut trouver, dans la partie principale de la page, les éléments suivants (en partant de haut en bas).
    sleep  ${L_S}
    Remove element  id=${main1}
    debug

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
# ATTENTION: le pointeur souris doit être hors de la fenêtre !!
# setup
    [TAGS]  RUN1
    Enable autologin as  encodeur
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Go to  ${PLONE_URL}/import_scanned
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25  additional_address_details=41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  description  Candidature spontanée  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  original_mail_date  20170314  date
    Fire transition  ${UID}  propose_to_n_plus_1
    Set field value  ${UID1}  title  Votre offre d'emploi d'agent administratif  str
    Set field value  ${UID1}  sender  ['${SENDER}']  references
    Set field value  ${UID1}  treating_groups  ${GRH}  str
    Set field value  ${UID1}  assigned_user  agent  str
    Fire transition  ${UID1}  propose_to_n_plus_1
    Enable autologin as  dirg
    Fire transition  ${UID}  propose_to_agent
    Fire transition  ${UID1}  propose_to_agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Select collection  incoming-mail/mail-searches/to_treat

    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10
# start video
    pause
# Ajouter une annexe
    ${note1}  Add title  Tutoriel vidéo iA.docs : comment ajouter une annexe...
    Sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add main note  L'action est identique qu'on soit sur une fiche courrier entrant, sortant ou une annexe.
    Sleep  ${L_S}
    Remove element  id=${note1}

#    ${note1}  Add pointy note  id=portal-globalnav
#    ...  Ceci est le bandeau des fonctionnalités  position=bottom  color=blue  width=200
#    sleep  ${N_S}
#    Remove element  id=${note1}
#
#    ${note1}  Add pointy note  id=portal-globalnav
#    ...  C'est par ici que vous accédez aux différentes parties d'iA.Docs  position=bottom  color=blue  width=300
#    sleep  ${N_S}
#    Remove element  id=${note1}
#
#    ${note1}  Add main note  Pour la démonstration, nous allons faire la démarche à partir de courrier entrant.
#    Sleep  ${L_S}
#    Remove element  id=${note1}
#
#    ${note1}  Add main note  Mais nous aurions tout aussi bien pu la faire en partant de courrier sortant.
#    Sleep  ${L_S}
#    Remove element  id=${note1}
#
#    ${note1}  Add pointy note  id=portaltab-incoming-mail
#    ...  Cliquez sur courrier entrant  position=bottom  color=blue  width=200
#    sleep  ${N_S}
#    Remove element  id=${note1}
#
#    GO to  ${PLONE_URL}/incoming-mail
#
#    # View courrier entrant
#    ${note1}  Add main note  Vous voici sur la page des courriers entrants
#    Sleep  ${N_S}
#    Remove element  id=${note1}
#
#    Wait until element is visible  css=.pretty_link a:first-child  10
#    ${note1}  Add pointy note  css=.pretty_link a:first-child
#    ...  Choisissez le courrier entrant sur lequel vous voulez ajouter une annexe  position=bottom  color=blue  width=300
#    sleep  ${N_S}
#    Remove element  id=${note1}
#
#    GO to  ${PLONE_URL}/incoming-mail/dmsincomingmail
#    sleep  ${S_S}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(5)
    ...  On va passer par le menu "Ajouter"  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(5)
    Remove element  id=${note1}
    Click element  css=table.actionspanel-no-style-table td:nth-child(5)
    sleep  ${N_S}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(5)
    ...  Et ensuite sélectionner "Annexe"  position=left  color=blue  width=200
    sleep  ${N_S}

    # Vue d'ajout
    GO to  ${PLONE_URL}/incoming-mail/dmsincomingmail/++add++dmsappendixfile

    ${note1}  Add pointy note  css=#form-widgets-IBasic-title  Ajoutez le titre de l'annexe  position=left  color=blue
    sleep  ${S_S}
    Remove element  id=${note1}

    Input text  id=form-widgets-IBasic-title  Annexe au dossier de Mr. Dupont Jean-Marc

    ${note1}  Add pointy note  css=#form-widgets-file-input  Ajoutez votre fichier à annexer  position=left  color=blue
    sleep  ${S_S}
    Remove element  id=${note1}

    Choose File  id=form-widgets-file-input  ${CURDIR}/annexe.pdf

    ${note1}  Add pointy note  id=form-buttons-save
    ...  Il reste à sauvegarder.  position=right  color=top  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=form-buttons-save
    Click element  form-buttons-save

    ${note1}  Add main note  L'annexe ajoutée est affichée.
    Sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=#portal-breadcrumbs #breadcrumbs-2
    ...  Pour remonter à la fiche, on va utiliser le fil d'ariane et cliquer sur le nom de la fiche  position=bottom  color=blue  width=200
    sleep  ${L_S}
    Remove element  id=${note1}
    Add clic  css=#portal-breadcrumbs #breadcrumbs-2
    Click element  css=#portal-breadcrumbs #breadcrumbs-2
    Wait until element is visible  css=.DV-pageImage  10

    ScrollDown

    ${note1}  Add pointy note  css=#content-core>fieldset
    ...  L'annexe ajoutée à la fiche courrier est listée dans un tableau en bas de la fiche  position=top  color=blue  width=300
    sleep  ${L_S}
    Remove element  id=${note1}

    ScrollUp

    Add title  Ce tutoriel vidéo est fini ;-)
    sleep  ${L_S}

Ajouter une tâche
# partie guide utilisation : Ajouter une tâche
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
    GO to  ${PLONE_URL}/
# Ajouter une tache
    ${note1}  Add main note  Bonjour et bienvenue dans ce tutorial sur: Comment ajouter une tâche dans iA.Docs
    Sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=portal-globalnav
    ...  Ceci est le bandeau des fonctionnalités  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=portal-globalnav
    ...  C'est par ici que vous accédez aux différentes parties d'iA.Docs  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add main note  Pour la démonstration, nous allons faire la démarche à partir de courrier entrant.
    Sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add main note  Mais nous aurions tout aussi bien pu la faire en partant de courrier sortant.
    Sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=portaltab-incoming-mail
    ...  Cliquez sur courrier entrant  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Remove element  id=${note1}

    GO to  ${PLONE_URL}/incoming-mail

    # View courrier entrant
    ${note1}  Add main note  Vous voici sur la page des courriers entrants
    Sleep  ${N_S}
    Remove element  id=${note1}

    Wait until element is visible  css=.pretty_link a:first-child  10
    ${note1}  Add pointy note  css=.pretty_link a:first-child
    ...  Choisissez le courrier entrant sur lequel vous voulez ajouter une tâche  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    GO to  ${PLONE_URL}/incoming-mail/dmsincomingmail-1
    sleep  ${S_S}

    # Sélectionner l'entrée "tâche"
    ${note1}  Add pointy note  css=tr td:nth-child(5)
    ...  Ajoutez une tâche  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Remove element  id=${note1}

    # Informations de la tâche
    GO to  ${PLONE_URL}/incoming-mail/dmsincomingmail-1/++add++task
    ${note1}  Add pointy note  css=#form-widgets-title  Ajoutez le titre de la tâche  position=left  color=blue
    sleep  ${S_S}
    Remove element  id=${note1}

    Input text  id=form-widgets-title  A faire: Tâche très importante

    ${note1}  Add pointy note  css=#form-widgets-ITask-assigned_group  Choisissez un service  position=left  color=blue
    sleep  ${N_S}
    Remove element  id=${note1}

    Select From List By Index  id=form-widgets-ITask-assigned_group  2

    ${note1}  Add pointy note  css=#form-widgets-ITask-assigned_user  Assignez quelqu'un comme par exemple: Fred Agent  position=left  color=blue
    sleep  ${S_S}
    Remove element  id=${note1}

    Select From List By Index  id=form-widgets-ITask-assigned_user  1

    ${note1}  Add pointy note  css=#form-buttons-save  Sauvegardez  position=left  color=blue
    sleep  ${N_S}
    Remove element  id=${note1}

    Click element  form-buttons-save
    sleep  ${S_S}

    # Fin création de la tâche
    ${note1}  Add pointy note  css=.portalMessage.info.success  Votre tâche a bien été créée  position=bottom  color=blue
    sleep  ${N_S}
    Remove element  id=${note1}

    GO to  ${PLONE_URL}/

    # View tâches
    ${note1}  Add pointy note  id=portaltab-tasks  Vérifions si la tâche est bien assignée à Fred Agent  position=bottom  color=blue
    sleep  ${N_S}
    Remove element  id=${note1}

    GO to  ${PLONE_URL}/tasks/task-searches

    Wait until element is visible  class=td_cell_assigned_user  20
    ${note1}  Add pointy note  css=.td_cell_assigned_user  Oui, elle lui est bien assignée  position=bottom  color=blue
    sleep  ${N_S}
    Remove element  id=${note1}

Utiliser les recherches
# partie guide utilisation : Utiliser les recherches
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
    GO to  ${PLONE_URL}/
# Recherche globale
    ${note1}  Add main note  Bonjour et bienvenue dans ce tutorial sur: L'utilisation des recherches d'iA.Docs
    Sleep  ${S_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=portal-globalnav
    ...  Ceci est le bandeau des fonctionnalités  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=portal-globalnav
    ...  C'est par ici que vous accédez aux différentes parties d'iA.Docs  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    # Champ recherche fulltext
    ${note1}  Add pointy note  id=livesearch0
    ...  Voici le champ de recherche globale  position=bottom  color=blue  width=200
    sleep  ${S_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=livesearch0
    ...  Il vous permet de faire une recherche fulltext sur les documents scannés  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    Click element  livesearch0
    sleep  ${S_S}

    # Input text
    ${note1}  Add pointy note  id=searchGadget
    ...  Entrez l'objet de votre recherche  position=left  color=blue  width=200
    sleep  ${N_S}
    Input text  name=SearchableText  Candidature
    Remove element  id=${note1}

    Wait until element is visible  css=.LSRow  20
    ${note1}  Add pointy note  css=.LSRow
    ...  La recherche globale trouve toutes les fiches contenant les termes recherchés  position=left  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=.LSRow
    ...  Cliquez dessus pour y accéder  position=left  color=blue  width=300
    sleep  ${S_S}
    Remove element  id=${note1}

    Click element  css=.LSRow
    sleep  ${N_S}

    # View fiche courrier
    ${note1}  Add pointy note  css=.pretty_link_content
    ...  Voilà, vous êtes bien sur la fiche courrier recherchée  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    sleep  ${L_S}

    GO to  ${PLONE_URL}/
    sleep  ${S_S}

# Recherche contextuelle
    Sleep  ${S_S}

    ${note1}  Add main note  Pour la recherche contextuelle maintenant
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=portaltab-incoming-mail
    ...  Cliquez sur courrier entrant ou sortant  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Remove element  id=${note1}

    #View courrier entrant
    GO to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  id=c2  20
    sleep  ${S_S}

    ${note1}  Add pointy note  id=c2
    ...  Voici le champ de recherche contextuelle  position=bottom  color=blue  width=200
    sleep  ${S_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=c2
    ...  Il vous permet de faire une recherche sur les informations encodées dans les fiches  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    Input text  id=c2  agent administratif

    ${note1}  Add pointy note  id=c2_button
    ...  Cliquez sur la loupe de recherche  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Remove element  id=${note1}

    Input text  id=c2  agent administratif

    Add clic  css=#c2_button
    Click element  c2_button
    sleep  ${S_S}

    # Fiche trouvée
    ${note1}  Add pointy note  css=.pretty_link
    ...  Il trouve bien la fiche recherchée  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Remove element  id=${note1}

    sleep  ${N_S}

    ${note1}  Add pointy note  id=c2
    ...  Effaçons le champ  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Remove element  id=${note1}

    Clear Element Text  id=c2

    Wait until element is visible  id=faceted_table  10
    ${note1}  Add pointy note  id=faceted_table
    ...  Nous avons de nouveau accès à tout le courrier  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    sleep  ${L_S}

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
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Set Suite Variable  ${CROP_MARGIN}  5
    Set Selenium Implicit Wait  2
    Set Selenium Speed  0.2
    Enable autologin as  Manager
    Set autologin username  dirg
    Go to  ${PLONE_URL}/robot_init
    Disable autologin
