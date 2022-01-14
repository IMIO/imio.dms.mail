*** Settings ***
Resource  plone/app/robotframework/keywords.robot
Resource  plone/app/robotframework/selenium.robot
Resource  common.robot

Library  Remote  ${PLONE_URL}/RobotRemote
Library  Selenium2Screenshots
Library  robot.libraries.DateTime

Suite Setup  Suite Setup
Suite Teardown  Close all browsers

*** Variables ***

# ${BROWSER} =  GoogleChrome
${RECORD} =  1  # set to 1 to made a pause at each test start, to record easierly
# Default values when RECORD = 1. If not, it's reduced in Suite Setup.
${C_S} =  1.5  # clic sleep
${S_S} =  2  # short sleep
${N_S} =  4  # normal sleep
${L_S} =  6  # longer sleep
${W_WIDTH} =  1840  # width 1200 1260 1280 1680
${W_HEIGHT} =  1035  # height 1920 2880 720 1050

*** Test Cases ***

Naviguer
    # setup
    [TAGS]  RUN01
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned?redirect=
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
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

    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Go to  ${PLONE_URL}/
    # start video
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
    # bandeau principal
    ${tit1}  Add title  Tutoriel vidéo iA.docs : Naviguer dans l'interface...
    sleep  ${L_S}
    Remove element  ${tit1}
    Highlight  id=portal-globalnav
    ${main1}  Add main note  Le bandeau principal permet un accès rapide aux différentes parties de l'application : courrier entrant, courrier sortant, tâches, annuaire de contacts et modèles de courriers.
    sleep  ${L_S}
    Remove element  id=${main1}
    Clear Highlight  id=portal-globalnav
    ${note1}  Add pointy note  id=portaltab-incoming-mail  On entre dans la partie "courrier entrant" en cliquant sur l'onglet.  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Add clic  id=portaltab-incoming-mail
    Remove element  id=${note1}
    # interface courrier entrant
    Click element  id=portaltab-incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    sleep  ${S_S}

    ${note1}  Add pointy note  id=collections-count-refresh  Une fois dans un des 3 premiers onglets, cette icône permet d'afficher le nombre d'éléments à gérer. On peut donc cliquer de temps en temps dessus afin de vérifier s'il y a des choses à gérer.  position=bottom  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}
    Add clic  id=collections-count-refresh
    Click element  id=collections-count-refresh
    ${note1}  Add pointy note  id=portaltab-incoming-mail  Le nombre de courriers entrants à gérer est à 2. On voit qu'il y a quelque chose à faire dans cette partie.  position=bottom  color=blue
    sleep  ${L_S}
    Remove element  id=${note1}

    Highlight  css=.portlet.portletWidgetCollection
    ${note1}  Add pointy note  css=.portlet.portletWidgetCollection  Le menu de gauche affiche des filtres prédéfinis, utiles à chaque utilisateur.  position=right  color=blue  width=400
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=.portlet.portletWidgetCollection  Il est possible de filtrer sur les courriers à traiter, en cours, dans le service, en copie, etc. Suivant le filtre sélectionné, le tableau de bord central se met à jour.  position=right  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}
    Clear Highlight  css=.portlet.portletWidgetCollection

    Highlight  css=div.faceted-tagscloud-collection-widget li:nth-child(4)
    ${note1}  Add pointy note  css=div.faceted-tagscloud-collection-widget li:nth-child(4)  Un compteur indique le nombre de courriers en attente d'un traitement...  position=right  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}
    Clear Highlight  css=div.faceted-tagscloud-collection-widget li:nth-child(4)
    Add clic  css=div.faceted-tagscloud-collection-widget li:nth-child(4)
    Select collection  incoming-mail/mail-searches/to_treat
    sleep  ${S_S}

    Highlight  id=faceted_table
    ${note1}  Add pointy note  id=faceted_table  Suivant la recherche sélectionnée (en gras), les éléments correspondants sont affichés ligne par ligne, avec les informations clés.  position=top  color=blue  width=400
    sleep  ${L_S}
    Clear Highlight  id=faceted_table
    Remove element  id=${note1}

    Highlight  css=.th_header_due_date
    ${note1}  Add pointy note  css=.th_header_due_date  Il est possible de trier par colonne, par exemple avec la date d'échéance.  position=top  color=blue  width=400
    sleep  ${L_S}
    Clear Highlight  css=.th_header_due_date
    Remove element  id=${note1}

    Highlight  css=.th_header_actions
    ${note1}  Add pointy note  css=.th_header_actions  La colonne "Actions" permet un accès rapide à des actions sur l'élément. En positionnant sa souris sur l'icône, on peut lire ce à quoi elle correspond.  position=top  color=blue  width=300
    sleep  ${L_S}
    Clear Highlight  css=.th_header_actions
    Remove element  id=${note1}

    Highlight  id=batch-actions
    ${note1}  Add pointy note  id=batch-actions  Les actions par lot permettent d'effectuer une action commune (si possible) sur tous les courriers sélectionnés dans la première colonne.  position=top  color=blue  width=400
    sleep  ${L_S}
    Clear Highlight  id=batch-actions
    Remove element  id=${note1}

    Highlight  id=faceted-center-column
    ${note1}  Add pointy note  id=faceted-center-column  Le filtre de recherche permet de trouver des éléments spécifique du tableau de bord.  position=bottom  color=blue  width=400
    sleep  ${L_S}
    Clear Highlight  id=faceted-center-column
    Remove element  id=${note1}

    Highlight  css=.LSBox
    ${note1}  Add pointy note  css=.LSBox  Une recherche plus globale permet de rechercher dans le texte océrisé des courriers, au cas où un élément ne serait pas trouvé par un tableau de bord.  position=bottom  color=blue  width=400
    sleep  ${L_S}
    Clear Highlight  css=.LSBox
    Remove element  id=${note1}

    ${main1}  Add main note  Les recherches sont expliquées plus en détail dans le guide "Utiliser les recherches".
    sleep  ${L_S}
    Remove element  id=${main1}

    Highlight  id=portal-breadcrumbs
    ${note1}  Add pointy note  id=breadcrumbs-1  Le fil d'ariane (présent sur chaque page) permet de se situer et de revenir au niveau du dessus à tout moment.  position=bottom  color=blue  width=400
    sleep  ${L_S}
    Clear Highlight  id=portal-breadcrumbs
    Remove element  id=${note1}

    Add end message

Traiter un courrier
    # setup
    [TAGS]  RUN02
    Enable autologin as  encodeur
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Go to  ${PLONE_URL}/import_scanned?redirect=
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
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
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
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
    ...  Des boutons permettant d’associer un libellé: "lu" (pour les courriers en copie), "suivi" (pour suivre des courriers).  position=left  color=blue  width=200
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
    ...  Il faut sauvegarder (si des modifications ont été apportées) ou annuler pour sortir du mode "édition".  position=right  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=form-buttons-cancel
    Click element  id=form-buttons-cancel

    # changement état
    ${main1}  Add main note  Le cycle de vie d’un élément (courrier, tâche) est constitué de différents états par lesquels l’élément transite depuis sa création, jusqu’à sa clôture.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Les états d'un courrier entrant sont par exemple: "En création", "À valider par le N+1" (ici nommé chef de service), "À traiter", "En traitement" et "Clôturé".
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

    ${main1}  Add main note  Les droits de l'utilisateur varient d'un état à l'autre. Par exemple, un agent ne pourra plus modifier un courrier quand il est dans l'état "Clôturé".
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
    ...  Si on clique à nouveau sur "Traiter".  position=top  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(3)
    Remove element  id=${note1}
    Click element  css=table.actionspanel-no-style-table td:nth-child(3)
    Wait until element is visible  css=.DV-pageImage  10

    ${note1}  Add pointy note  css=#parent-fieldname-title span.pretty_link_icons img:nth-child(1)
    ...  Une icône spécifique indique qu'on revient à un état déjà rencontré.  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    Add end message

Répondre à un courrier
    # setup
    [TAGS]  RUN03
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned?redirect=
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
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
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
    # répondre
    ${main1}  Add title  Tutoriel vidéo iA.docs : comment répondre à un courrier entrant...
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Considérant qu'on est sur la vue d'un courrier entrant...
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(6)
    ...  On va passer par le bouton "Répondre"  position=top  color=blue  width=200
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(6)
    Remove element  id=${note1}
    Click element  css=table.actionspanel-no-style-table td:nth-child(6)
    Wait until element is visible  css:body.template-reply #formfield-form-widgets-external_reference_no  10

    ${main1}  Add main note  Le formulaire proposé est complété par défaut avec les données du courrier entrant. Tous les champs peuvent cependant être modifiés.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Passons en revue quelques particularités de certains champs.
    sleep  ${N_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  id=formfield-form-widgets-IDublinCore-title
    ...  Le titre peut être préfixé par une valeur configurée (ici "Réponse: ").  position=right  color=blue  width=600
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=formfield-form-widgets-sender
    ...  L'expéditeur est déduit de l'utilisateur connecté. Il correspondra aux données d'expédition renseignées dans le courrier généré ou l'email.  position=right  color=blue  width=800
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=formfield-form-widgets-send_modes
    ...  Le champ "Formes d'envoi" est important car il va déterminer la méthode d'envoi du courrier. Si une valeur avec email est sélectionnée, alors des boutons complémentaires vont apparaître pour gérer l'email. Cet aspect est expliqué dans le guide "Envoi d'un email sortant".  position=right  color=blue  width=1000
    sleep  ${N_S}
    sleep  ${L_S}
    Remove element  id=${note1}

    ScrollDown
    sleep  ${N_S}

    ${note1}  Add pointy note  id=form-buttons-cancel
    ...  Il faut sauvegarder pour confirmer la réponse.  position=right  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=form-buttons-save
    Click element  id=form-buttons-save
    Wait until element is visible  css:body.portaltype-dmsoutgoingmail #formfield-form-widgets-external_reference_no  10

    # fiche créée
    ${main1}  Add main note  Une fiche "courrier sortant" a été créée, dans l'état initial "en création".
    sleep  ${N_S}
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=div.faceted-tagscloud-collection-widget-portlet li:nth-child(9)
    ...  Les états possibles pour le courrier sortant sont montrés dans les recherches commençant par "État".  position=top  color=blue  width=250
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(5)
    ...  On va pouvoir générer un document bureautique depuis un modèle. Cet aspect est expliqué plus en détails dans le guide "Créer un document bureautique...".  position=top  color=blue  width=600
    sleep  ${L_S}
    Remove element  id=${note1}

    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature-a-un-poste-douvrier-communal/create_main_file?filename=Reponse+candidature+ouvrier+communal.odt&title=Modèle+de+base&mainfile_type=dmsommainfile&redirect=
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature-a-un-poste-douvrier-communal
    Wait until element is visible  css:body.portaltype-dmsoutgoingmail #formfield-form-widgets-external_reference_no  10

    ${main1}  Add main note  Une fois le document ajouté, la fiche se présente comme ci-dessous.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(2)
    ...  Si le service a un N+1, il est possible de lui envoyer le courrier pour validation.  position=top  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(3)
    ...  Sinon, quand il y a bien un fichier ged dans la fiche, on peut mettre le courrier à la signature manuscrite.  position=top  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(4)
    ...  On peut également l'indiquer comme ayant été expédié.  position=top  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}

    Add end message

Créer un courrier sortant
    # setup
    [TAGS]  RUN04
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Enable autologin as  agent
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  css=div.table_faceted_results  10
    # start video
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
    # créer cs
    ${main1}  Add title  Tutoriel vidéo iA.docs : comment créer un courrier sortant...
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Considérant qu'on est dans l'onglet "courrier sortant"...
    sleep  ${N_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  id=newOMCreation
    ...  On peut créer un nouveau courrier sortant en cliquant sur cette icône.  position=right  color=blue  width=300
    sleep  ${L_S}
    Add clic  id=newOMCreation
    Remove element  id=${note1}
    Click element  id=newOMCreation
    Wait until element is visible  css=.template-dmsoutgoingmail #formfield-form-widgets-sender  10

    Input text  name=form.widgets.IDublinCore.title  Annonce de la réfection des trottoirs Rue des Papillons
    sleep  ${S_S}

    ${note1}  Add pointy note  id=formfield-form-widgets-recipients
    ...  On peut chercher un contact dans l'annuaire en tapant le début des mots composant son titre. Si le bon contact n'est pas trouvé, il est possible de le rajouter. Cet aspect est expliqué plus en détails dans le guide "Ajouter un contact...".  position=right  color=blue  width=1000
    sleep  ${S_S}
    sleep  ${L_S}
    Remove element  id=${note1}
    Input text  name=form.widgets.recipients.widgets.query  leduc
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    sleep  ${N_S}
    Click element  css=.ac_results:not([style*="display: none"]) li
    sleep  ${S_S}

    ${note1}  Add pointy note  id=formfield-form-widgets-treating_groups
    ...  Le service traitant est le service de gestion du courrier.  position=right  color=blue  width=800
    sleep  ${L_S}
    Remove element  id=${note1}
    Click element  id=form-widgets-treating_groups
    Select From List By Index  id=form-widgets-treating_groups  6

    ${note1}  Add pointy note  id=formfield-form-widgets-ITask-assigned_user
    ...  Seuls les utilisateurs du service traitant choisi sont considérés. L'utilisateur courant est présélectionné.  position=right  color=blue  width=800
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  id=formfield-form-widgets-sender
    ...  L'expéditeur est déduit de l'utilisateur connecté. Il correspondra aux données d'expédition renseignées dans le courrier généré ou l'email.  position=right  color=blue  width=800
    sleep  ${L_S}
    Remove element  id=${note1}
    Click element  id=form_widgets_sender_select_chzn
    sleep  ${S_S}
    Input text  css=.chzn-search input  voiries
    sleep  ${S_S}
    Click element  css=#form_widgets_sender_select_chzn ul.chzn-results li[class=active-result]

    ${note1}  Add pointy note  id=formfield-form-widgets-send_modes
    ...  Le champ "Formes d'envoi" est important car il va déterminer la méthode d'envoi du courrier. Si une valeur avec email est sélectionnée, alors des boutons complémentaires vont apparaître pour gérer l'email. Cet aspect est expliqué dans le guide "Envoi d'un email sortant".  position=right  color=blue  width=1000
    sleep  ${N_S}
    sleep  ${L_S}
    Remove element  id=${note1}
    Select checkbox  id=form-widgets-send_modes-0
    sleep  ${S_S}

    ScrollDown
    sleep  ${N_S}

    ${note1}  Add pointy note  id=form-buttons-cancel
    ...  Il faut sauvegarder pour confirmer la réponse.  position=right  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=form-buttons-save
    Click element  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10

    # fiche créée
    ${main1}  Add main note  Une fiche "courrier sortant" a été créée, dans l'état initial "en création".
    sleep  ${N_S}
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=div.faceted-tagscloud-collection-widget-portlet li:nth-child(9)
    ...  Les états possibles pour le courrier sortant sont montrés dans les recherches commençant par "État".  position=top  color=blue  width=250
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(5)
    ...  On va pouvoir générer un document bureautique depuis un modèle. Cet aspect est expliqué plus en détails dans le guide "Créer un document bureautique...".  position=top  color=blue  width=600
    sleep  ${L_S}
    Remove element  id=${note1}

    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-des-papillons/create_main_file?filename=Reponse+candidature+ouvrier+communal.odt&title=Modèle+de+base&mainfile_type=dmsommainfile&redirect=
    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-des-papillons
    Wait until element is visible  css:body.portaltype-dmsoutgoingmail #formfield-form-widgets-external_reference_no  10

    ${main1}  Add main note  Une fois le document ajouté, la fiche se présente comme ci-dessous.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(2)
    ...  Si le service a un N+1, il est possible de lui envoyer le courrier pour validation.  position=top  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(3)
    ...  Sinon, quand il y a bien un fichier ged dans la fiche, on peut mettre le courrier à la signature manuscrite.  position=top  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(4)
    ...  On peut également l'indiquer comme ayant été expédié.  position=top  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}

    Add end message

Créer un document bureautique
# partie guide utilisation : Créer un courrier bureautique
# Setup
    [TAGS]  RUN05
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Enable autologin as  agent
    ${RECIPIENT} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25  additional_address_details=41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${SENDER} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/agent/agent-voiries
    ${VOIRIES} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-technique/voiries
    ${UID} =  Create content  type=dmsoutgoingmail  container=/${PLONE_SITE_ID}/outgoing-mail  id=annonce-de-la-refection-des-trottoirs-rue-des-papillons
    ...  title=Annonce de la réfection des trottoirs Rue des Papillons  internal_reference_number=S0001
    Set field value  ${UID}  send_modes  ['post', 'email']  list
    Set field value  ${UID}  treating_groups  ${VOIRIES}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  sender  ${SENDER}  str
    Set field value  ${UID}  recipients  ['${RECIPIENT}']  references
    Set field value  ${UID}  mail_type  courrier  str
    ${date}=  Get Current Date  local  exclude_millis=yes
    ${convert}=  Convert Date  ${date}  result_format=%d/%m/%Y
    Set field value  ${UID}  mail_date  ${convert}  date%d/%m/%Y
    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-des-papillons/create_main_file?filename=Reponse+candidature+ouvrier+communal.odt&title=Modèle+de+base&mainfile_type=dmsommainfile&redirect=
    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-des-papillons
# start video
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
# visualisation TODO à corriger
    ${main1}  Add title  Tutoriel vidéo iA.docs : Comment créer un document bureautique
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Repartons de l'exemple du courrier sortant créé dans le guide "Créer un courrier sortant"
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=table a.version-link:first-child
    ...  On constate qu'un document est déjà présent sur la fiche: Modèle de base  position=left  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=.DV-pageCollection
    ...  Le document bureautique généré est prérempli avec les données déjà encodées dans la fiche. Celles-ci peuvent être modifiées ou complétées.  position=left  color=blue  width=300
    sleep  ${L_S}
    Remove element  id=${note1}

   ${note1}  Add pointy note  css=#formfield-form-widgets-send_modes label
    ...  Pour pouvoir créer un document bureautique à partir d'un modèle, il faut que le champ "Formes d'envoi" contienne une entrée "lettre".  position=top  color=blue  width=400
    Highlight  css=#form-widgets-send_modes label
    sleep  ${L_S}
    Clear Highlight  css=#form-widgets-send_modes label
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=.apButton.apButtonAction.apButtonAction_create-from-template
    ...  Il faut ensuite sélectionner le bouton "Créer depuis modèle"  position=bottom  color=blue  width=400
    Highlight  css=.apButton.apButtonAction.apButtonAction_create-from-template
    sleep  ${L_S}
    Clear Highlight  css=.apButton.apButtonAction.apButtonAction_create-from-template
    Remove element  id=${note1}

    Add clic  css=.apButton.apButtonAction.apButtonAction_create-from-template
    Click element  css=.apButton.apButtonAction.apButtonAction_create-from-template

    ${main1}  Add main note  Les modèles sont communs ou spécifiques à des services. On en choisit un
    sleep  ${L_S}
    Remove element  id=${main1}

    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}

    Add clic  css=.fancytree-exp-cl span.fancytree-expander
    Click element  css=.fancytree-exp-cl span.fancytree-expander

    ${note1}  Add main note  On choisit "Modèle type"
    sleep  ${S_S}
    Remove element  id=${note1}

    Add clic  css=.fancytree-exp-nl span:nth-child(2)
    Click element  css=.fancytree-exp-nl span:nth-child(2)

    GO to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-des-papillons

    ${main1}  Add main note  Le document bureautique s'ouvre maintenant dans LibreOffice
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  La partie édition du document dans LibreOffice ne sera pas détaillée dans cette vidéo
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Mais votre document sera généré selon le template sélectionné
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Il vous suffira de remplacer la ligne "Texte" dans LibreOffice par le contenu de votre document et de sauvegarder
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Le document sera ajouté à la fiche courrier
    sleep  ${L_S}
    Remove element  id=${main1}

    # Wait until element is visible  css=table a.version-link:first-child  10
    # ${note1}  Add pointy note  css=table a.version-link:first-child
    # ...  On voit bien qu'un nouveau document est apparu dans la liste des documents de la fiche courrier et que c'est un "Modèle type"  position=left  color=blue  width=300
    # sleep  ${N_S}
    # Remove element  id=${note1}
    Wait until element is visible  css=table tbody tr:first-child  10
    ${note1}  Add pointy note  css=table tbody tr:first-child
    ...  On voit bien qu'un nouveau document est apparu dans la liste des documents de la fiche courrier et que c'est un "Modèle type"  position=left  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}

    ${note1}  Add pointy note  css=.DV-cover
    ...  La visualisation du document bureautique nous montre qu'un document a bien été créé à partir d'un template  position=left  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add main note  Pour en savoir plus sur la création et la modification de templates, veuillez vous reporter au point "2.10 - Gestion des modèles" de la documentation écrite
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add main note  Ou rendez-vous sur la vidéo "Gérer les modèles"
    sleep  ${N_S}
    Remove element  id=${note1}

    Add end message

Transférer un email entrant
    # setup
    [TAGS]  RUN06
    Enable autologin as  encodeur
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Go to  ${PLONE_URL}/import_scanned?redirect=
    Go to  ${PLONE_URL}/import_scanned?ptype=dmsincoming_email&number=1&redirect=&only=email1.pdf
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
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
    ${UID2} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/reservation-de-la-salle-le-foyer
    ${EVEN} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/evenements
    Set field value  ${UID2}  treating_groups  ${EVEN}  str
    Enable autologin as  dirg
    Fire transition  ${UID}  propose_to_agent
    Fire transition  ${UID1}  propose_to_agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Select collection  incoming-mail/mail-searches/to_treat
    # start video
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
    ${note1}  Add title  Tutoriel vidéo iA.docs : comment transférer un email entrant...
    Sleep  ${L_S}
    Remove element  id=${note1}

    ${main1}  Add main note  Depuis votre client mail, vous allez pouvoir transférer un email sélectionné vers l'application iA.docs pour en faire une fiche courrier entrant.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Attention: la façon de transférer l'email est différente. Ce n'est pas un transfert "simple". Il est nécessaire de transférer l'email "en tant que pièce jointe".
    sleep  ${L_S}
    Remove element  id=${main1}

    Go to  ${PLONE_URL}/outlook-ruban.jpg/view

    ${main1}  Add main note  Dans Outlook, par exemple, le transfert "en tant que pièce jointe" se trouve dans le ruban (comme montré dans l'image ci-dessous). On y voit aussi le raccourci (Ctrl + Alt + F).
    sleep  ${L_S}
    sleep  ${S_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Une fois le transfert effectué, l'email va initier la création d'une nouvelle fiche... (dans les 3 minutes maximum)
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Revenons dans le tableau de bord "rafraichi" de l'agent, afin de visualiser la fiche créée.
    sleep  ${N_S}
    Remove element  id=${main1}

    Enable autologin as  dirg
    Fire transition  ${UID2}  propose_to_agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Select collection  incoming-mail/mail-searches/to_treat

    ${note1}  Add pointy note  css=#faceted_table tr:nth-child(1) td.pretty_link
    ...  On peut voir la nouvelle fiche (avec une icône spécifique), directement visible par l'agent. On va cliquer sur son intitulé pour l'ouvrir.  position=top  color=blue  width=300
    sleep  ${L_S}
    Add clic  css=#faceted_table tr:nth-child(1) td.pretty_link
    Remove element  id=${note1}
    Click element  css=#faceted_table tr:nth-child(1) td.pretty_link
    Wait until element is visible  css=.DV-pageImage  10

    ${main1}  Add main note  Les données de la fiche ont été préremplies avec les données de l'email. Si l'agent qui a transféré est bien défini dans iA.docs, le service traitant est sélectionné et la fiche est mise "À traiter" (suivant la configuration). Sinon la fiche reste en création.
    sleep  ${L_S}
    sleep  ${S_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Si l'expéditeur d'origine a été trouvé dans l'annuaire (via son adresse email), il est sélectionné. Ce n'est pas le cas ici, on va modifier la fiche.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(1)
    ...  On va cliquer sur cette icône pour modifier les données de la fiche.  position=top  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(1)
    Remove element  id=${note1}
    Click element  css=table.actionspanel-no-style-table td:nth-child(1)
    Wait until element is visible  css:body.template-dmsdocument-edit #formfield-form-widgets-external_reference_no  10

    ${main1}  Add main note  On peut modifier les champs qui nécessitent un changement...
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  id=formfield-form-widgets-sender
    ...  On peut chercher un contact dans l'annuaire en tapant le début des mots composant son titre. Si le bon contact n'est pas trouvé, il est possible de le rajouter.  position=right  color=blue  width=800
    sleep  ${L_S}
    Remove element  id=${note1}
    Input text  name=form.widgets.sender.widgets.query  geulett
    Wait until element is visible  css=#formfield-form-widgets-sender div.addnew-block a.addnew  10
    ${note1}  Add pointy note  css=#formfield-form-widgets-sender div.addnew-block a.addnew
    ...  Aucun contact de ce nom trouvé! Imaginons qu'on crée un nouveau contact via le lien "Créer Contact"... Cet aspect est expliqué plus en détails dans le guide "Ajouter un contact".   position=right  color=blue  width=800
    sleep  ${L_S}
    Remove element  id=${note1}
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Stéphan  lastname=Geulette  zip_code=5032  city=Isnes  street=Rue Léon Morel  number=1  email=stephan.geulette@email.be
    Input text  name=form.widgets.sender.widgets.query  geulette
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    sleep  ${S_S}
    Add clic  css=.ac_results:not([style*="display: none"]) li
    Click element  css=.ac_results:not([style*="display: none"]) li
    sleep  ${N_S}

    ScrollDown

    ${note1}  Add pointy note  id=form-buttons-cancel
    ...  Il faut sauvegarder (si des modifications ont été apportées) ou annuler pour sortir du mode "édition".  position=right  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=form-buttons-save
    Click element  id=form-buttons-save
    Wait until element is visible  css=.DV-pageImage  10

    ${main1}  Add main note  Une fois les données nécessaires ajoutées, le traitement peut continuer en modifiant l'état de la fiche via les boutons bleus de la barre...
    sleep  ${L_S}
    Remove element  id=${main1}

    Add end message

Envoyer un email sortant
    # setup
    [TAGS]  RUN07
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Enable autologin as  agent
    ${RECIPIENT} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${SENDER} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/agent/agent-voiries
    ${VOIRIES} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-technique/voiries
    ${UID} =  Create content  type=dmsoutgoingmail  container=/${PLONE_SITE_ID}/outgoing-mail  id=annonce-de-la-refection-des-trottoirs-rue-des-papillons
    ...  title=Annonce de la réfection des trottoirs Rue des Papillons  internal_reference_number=S0001
    Set field value  ${UID}  send_modes  ['post', 'email']  list
    Set field value  ${UID}  treating_groups  ${VOIRIES}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  sender  ${SENDER}  str
    Set field value  ${UID}  recipients  ['${RECIPIENT}']  references
    Set field value  ${UID}  mail_type  courrier  str
    ${date}=  Get Current Date  local  exclude_millis=yes
    ${convert}=  Convert Date  ${date}  result_format=%d/%m/%Y
    Set field value  ${UID}  mail_date  ${convert}  date%d/%m/%Y
    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-des-papillons/create_main_file?filename=Reponse+candidature+ouvrier+communal.odt&title=Modèle+de+base&mainfile_type=dmsommainfile&redirect=
    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-des-papillons
    # start video
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
    # visualisation
    ${main1}  Add title  Tutoriel vidéo iA.docs : comment envoyer un email sortant...
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Repartons de l'exemple du courrier sortant créé dans le guide "Créer un courrier sortant"...
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  formfield-form-widgets-send_modes
    ...  Pour pouvoir envoyer un email, il faut que le champ "Formes d'envoi" contienne une entrée "email".  position=right  color=blue  width=400
    Highlight  formfield-form-widgets-send_modes
    sleep  ${L_S}
    Clear Highlight  formfield-form-widgets-send_modes
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(8)
    ...  Dans ce cas alors, un bouton intitulé "Rédiger email" s'affiche. On va cliquer dessus.  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(8)
    Remove element  id=${note1}
    Click element  css=table.actionspanel-no-style-table td:nth-child(8)
    Wait until element is visible  css:body.template-dmsdocument-edit #formfield-form-widgets-email_body  10

    ${main1}  Add main note  Le formulaire de rédaction d'un email est prérempli avec les données déjà encodées dans la fiche. Celles-ci peuvent être modifiées ou complétées.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  id=formfield-form-widgets-email_cc
    ...  On peut rajouter une adresse email en copie.  position=top  color=blue  width=500
    sleep  ${S_S}
    Input text  form-widgets-email_cc  autre.agent@macommune.be
    Remove element  id=${note1}
    sleep  ${S_S}

    ${note1}  Add pointy note  formfield-form-widgets-email_attachments
    ...  On peut sélectionner une pièce jointe déjà dans la fiche (le fichier ged ou les annexes).  position=top  color=blue  width=400
    Highlight  formfield-form-widgets-email_attachments
    sleep  ${N_S}
    Clear highlight  formfield-form-widgets-email_attachments
    Add clic  css=#formfield-form-widgets-email_attachments input#form-widgets-email_attachments-0
    Remove element  id=${note1}
    Click element  css=#formfield-form-widgets-email_attachments input#form-widgets-email_attachments-0
    sleep  ${S_S}

    ${note1}  Add pointy note  id=formfield-form-widgets-email_body
    ...  Le corps de l'email est déjà prérempli avec la signature générée de l'agent. On peut le compléter manuellement ou utiliser un modèle.  position=top  color=blue  width=500
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=#formfield-form-widgets-email_body a.cke_button__templates
    ...  Cette icône permet d'accéder aux modèles d'email.  position=right  color=blue  width=600
    sleep  ${N_S}
    Add clic  css=#formfield-form-widgets-email_body a.cke_button__templates
    Remove element  id=${note1}
    Click element  css=#formfield-form-widgets-email_body a.cke_button__templates

    ${main1}  Add main note  Les modèles sont communs ou spécifiques à des services. On en choisit un...
    sleep  ${L_S}
    Remove element  id=${main1}
    click element  css=div.cke_tpl_list a:nth-child(1) span.cke_tpl_title

    ${note1}  Add pointy note  id=formfield-form-widgets-email_body
    ...  Le modèle s'est inséré au début du texte (ou à la place du curseur si on était déjà dans le texte).   position=top  color=blue  width=500
    sleep  ${L_S}
    Remove element  id=${note1}

    ScrollDown
    ${note1}  Add pointy note  id=form-buttons-cancel
    ...  Il faut sauvegarder pour confirmer (ou annuler si on a fait une erreur et qu'on veut recommencer)...  position=right  color=blue  width=500
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=form-buttons-save
    Click element  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(8)
    ...  Le bouton "Rédiger email" est passé au vert (indiquant que l'email est rédigé).  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  form-groups-email
    ...  Les informations de l'email sont affichées ci-dessous.  position=top  color=blue  width=300
    sleep  ${L_S}
    Remove element  id=${note1}

    ScrollDown
    sleep  ${N_S}
    ScrollUp

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(10)
    ...  Un bouton intitulé "Envoyer email" s'affiche. On peut cliquer dessus pour envoyer l'email.  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(10)
    Remove element  id=${note1}
    # Simulation envoi
    ${date}=  Get Current Date  local  exclude_millis=yes
    ${convert}=  Convert Date  ${date}  result_format=%Y-%m-%d %H:%M
    Set field value  ${UID}  email_status  Email envoyé le ${convert}  str
    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-des-papillons
    sleep  ${S_S}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(11)
    ...  Si l'envoi s'est bien déroulé, le bouton est passé au vert.  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  formfield-form-widgets-email_status
    ...  La date d'envoi est indiquée.  position=top  color=blue  width=300
    Highlight  formfield-form-widgets-email_status
    sleep  ${N_S}
    Clear highlight  formfield-form-widgets-email_status
    Remove element  id=${note1}

    ${main1}  Add main note  Suivant la configuration de l'outil, la fiche peut être clôturée automatiquement après l'envoi réussi de l'email...
    sleep  ${L_S}
    Remove element  id=${main1}
    Fire transition  ${UID}  mark_as_sent
    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-des-papillons
    sleep  ${N_S}

    ${note1}  Add pointy note  css=div.viewlet_workflowstate
    ...  Dans ce cas, la fiche n'est plus modifiable et l'état est  position=left  color=blue  width=500
    sleep  ${L_S}

    ${main1}  Add main note  Pour information, l'email envoyé par iA.docs ne se retrouvera pas dans la boîte email de l'agent. Il est juste visible dans iA.docs.
    sleep  ${L_S}
    Remove element  id=${main1}

    Add end message

Valider un courrier entrant
    # Setup
    [TAGS]  RUN08
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned?redirect=
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${SENDER1} =  Path to uid  /${PLONE_SITE_ID}/contacts/jeancourant
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  description  Candidature spontanée  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  treating_groups  ${GRH}  str
    # Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  original_mail_date  20170314  date
    Fire transition  ${UID}  propose_to_n_plus_1
    Set field value  ${UID1}  title  Votre offre d'emploi d'agent administratif  str
    Set field value  ${UID1}  sender  ['${SENDER1}']  references
    Set field value  ${UID1}  treating_groups  ${GRH}  str
    # Set field value  ${UID1}  assigned_user  agent  str
    Fire transition  ${UID1}  propose_to_n_plus_1
    Enable autologin as  chef
    GO to  ${PLONE_URL}/incoming-mail/

    # Start Video
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
    ${tit1}  Add title  Tutoriel vidéo iA.docs : Comment valider un courrier
    sleep  ${L_S}
    Remove element  id=${tit1}

    ${main1}  Add main note  La validation d'un courrier est nécessaire quand celui-ci se trouve dans un état "À valider par ..." le DG ou un niveau N+...
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Considérant qu'on est connecté en tant que N+1 (niveau dénommé ici "chef de service").
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  portaltab-incoming-mail
    ...  L'utilisateur s'est rendu dans l'onglet "Courrier entrant" car il indique 2 éléments à gérer...  position=bottom  color=blue  width=300
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=#c1_widget li:nth-child(4)
    ...  La recherche "À valider" est affichée quand on est validateur. On l'utilise...  position=right  color=blue  width=500
    Highlight  css=#c1_widget li:nth-child(4)
    sleep  ${L_S}
    Clear highlight  css=#c1_widget li:nth-child(4)
    Remove element  id=${note1}
    Add clic  css=#c1_widget li:nth-child(4) span
    Select collection  incoming-mail/mail-searches/to_validate

    ${note1}  Add main note  On voit dans le tableau de bord les 2 courriers à valider, avec leurs données principales...
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=#faceted_table tr:nth-child(2) td.pretty_link
    ...  On va cliquer sur l'intitulé d'un courrier pour l'ouvrir.  position=top  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=#faceted_table tr:nth-child(2) td.pretty_link
    Remove element  id=${note1}
    Click element  css=#faceted_table tr:nth-child(2) td.pretty_link

    ${main1}  Add main note  Les boutons en bleu sont les transitions "arrière" possibles, si on veut remettre la fiche dans un état précédent.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  Il n'y a pas de transition pour "avancer" car la fiche n'est pas complète.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  formfield-form-widgets-ITask-assigned_user
    ...  En effet, l'application peut être configurée pour exiger un "utilisateur assigné" au plus tard au niveau N+1.  position=top  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(1)
    ...  On peut soit "modifier" la fiche si plusieurs changements sont nécessaires.  position=top  color=blue  width=300
    sleep  ${N_S}

    ${note2}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(8)
    ...  soit utiliser le bouton d'assignation.  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Remove element  id=${note2}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(8)
    Click element  css=table.actionspanel-no-style-table td:nth-child(8) select
    Add clic  css=table.actionspanel-no-style-table td:nth-child(8) select option:nth-child(1)
    Select From List By Value  css=table.actionspanel-no-style-table td:nth-child(8) select  agent
    Wait until element is visible  css=table.actionspanel-no-style-table input.apButtonWF_propose_to_agent  10

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(4)
    ...  La transition suivante est maintenant affichée.  position=top  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(4)
    Remove element  id=${note1}
    Click element  css=table.actionspanel-no-style-table td:nth-child(4)
    Wait until element is visible  css=table.actionspanel-no-style-table input.apButtonWF_treat  10

    ${note1}  Add pointy note  css=.viewlet_workflowstate
    ...  L'état a changé: le courrier est maintenant visible par les agents du service.  position=left  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  query-nextprev-prev
    ...  On peut utiliser les liens "précédent/suivant" pour passer à un autre courrier à valider.  position=left  color=blue  width=400
    sleep  ${N_S}
    Add clic  query-nextprev-prev
    Remove element  id=${note1}
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail-1

    ${note1}  Add main note  Il suffit de refaire les mêmes manipulations sur ce courrier...
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add main note  On peut également faire les mêmes manipulations à partir du tableau de bord.
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=div.faceted-tagscloud-collection-widget-portlet li:nth-child(4)
    ...  On se remet sur le tableau de bord via le menu de gauche.  position=top  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=div.faceted-tagscloud-collection-widget-portlet li:nth-child(4) span
    Remove element  id=${note1}
    Select collection  incoming-mail/mail-searches/to_validate

    ${note1}  Add pointy note  css=#faceted_table tr:nth-child(1) td.td_cell_actions
    ...  On peut aussi assigner et changer l'état grâce aux icônes d'actions.  position=left  color=blue  width=300
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add main note  Il est également possible de valider plusieurs éléments en utilisant les actions par lot, en bas du tableau.
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add main note  Le bouton "Changer l'utilisateur assigné" peut définir un utilisateur commun pour les fiches sélectionnées dans la première colonne.
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add main note  Le bouton "Changer l'état" peut ensuite faire transiter les fiches vers l'agent.
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add main note  Les boutons d'actions sont expliqués plus en détail dans le guide "Actions dans les tableaux de bord".
    sleep  ${L_S}
    Remove element  id=${note1}

    Add end message

Ajouter un contact
    # setup
    [TAGS]  RUN09
    Enable autologin as  encodeur
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Go to  ${PLONE_URL}/import_scanned?redirect=&only=59.PDF
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  description  Candidature spontanée  str
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  original_mail_date  20170314  date
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/edit
    Wait until element is visible  css=.DV-pageImage  10
    # Start Video
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
    # édition
    ${tit1}  Add title  Tutoriel vidéo iA.docs : Comment utiliser le champ de sélection d'un contact et comment en ajouter un nouveau.
    Sleep  ${L_S}
    Sleep  ${S_S}
    Remove element  id=${tit1}

    ${main1}  Add main note  L'utilisation de ce champ est identique qu'il s'agisse de l'expéditeur dans un courrier entrant ou du destinataire dans un courrier sortant.
    Sleep  ${L_S}
    Remove element  id=${main1}

    ${main1}  Add main note  On va utiliser le champ "Expéditeurs" d'un courrier entrant...
    Highlight  formfield-form-widgets-sender
    Sleep  ${L_S}
    Clear highlight  formfield-form-widgets-sender
    Remove element  id=${main1}

    ${note1}  Add pointy note  formfield-form-widgets-sender
    ...  La première démarche est d'effectuer une recherche en utilisant le début d'un ou plusieurs mots de l'intitulé d'un contact.  position=top  color=blue  width=600
    sleep  ${L_S}
    Remove element  id=${note1}

    Input text  name=form.widgets.sender.widgets.query  le
    ${note1}  Add pointy note  formfield-form-widgets-sender
    ...  Il faut au moins 2 caractères par terme et se limiter aux nom et prénom pour une personne ou à l'intitulé pour une organisation.  position=top  color=blue  width=600
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  formfield-form-widgets-sender
    ...  Le résultat affiché est limité à 50. En cas de nombreux résultats, il faut alors affiner la recherche...  position=top  color=blue  width=600
    sleep  ${L_S}
    Remove element  id=${note1}

    Input text  name=form.widgets.sender.widgets.query  led marc
    ${note1}  Add pointy note  formfield-form-widgets-sender
    ...  Si on indique plusieurs termes, il n'est pas nécessaire de terminer les premiers par une astérisque "*" (contrairement aux filtres et recherches texte ailleurs).  position=top  color=blue  width=600
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  formfield-form-widgets-sender
    ...  Si le contact recherché n'apparaît pas, on peut alors le créer.  position=top  color=blue  width=600
    sleep  ${N_S}
    Remove element  id=${note1}

    # Create contact
    ${note1}  Add pointy note  css=.addnew
    ...  En utilisant ce lien (qui apparaît après une recherche)  position=bottom  color=blue  width=400
    sleep  ${N_S}
    Remove element  id=${note1}

    ${main1}  Add main note  Afin de montrer toutes les possibilités d'utilisation, nous allons d'abord créer une organisation, ensuite un sous-niveau dans une organisation, ensuite une personne et enfin une fonction occupée par une personne dans une organisation.
    Sleep  ${L_S}
    Sleep  ${L_S}
    Remove element  id=${main1}

#    Input text  name=form.widgets.sender.widgets.query  led marc
#    sleep  1

    Add clic  css=.addnew
    Click element  css=.addnew
    Wait until element is visible  css=.overlay-contact-addnew  10
    sleep  ${S_S}

    # Create organization
    Update element style  css=#oform-widgets-organization-autocomplete div.addnew-block  width  inherit
    ${note1}  Add pointy note  css=#oform-widgets-organization-widgets-query
    ...  On recherche une organisation...  position=top  color=blue  width=400
    Input text  name=oform.widgets.organization.widgets.query  IMIO
    sleep  ${N_S}
    Remove element  id=${note1}
    # Update element style  css=#oform-widgets-organization-autocomplete .addnew  padding-right  1em
    ${note1}  Add pointy note  css=#oform-widgets-organization-widgets-query
    ...  Pas de résultat: on va la créer...  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    Add Clic  css=#oform-widgets-organization-autocomplete .addnew
    Click element  css=#oform-widgets-organization-autocomplete .addnew
    Wait until element is visible  id=pb_2  10
    Update element style  id=formfield-form-widgets-activity  display  none

    ${note1}  Add main note  Par défaut, l'intitulé est repris du terme recherché précédemment. On complète le reste de la fiche signalétique: tout n'est pas nécessaire ! L'adresse postale et l'adresse email sont importantes afin de savoir répondre...
    Sleep  ${L_S}
    Remove element  id=${note1}

    Input text  name=form.widgets.enterprise_number  BE0841470248
    sleep  ${S_S}
    Add clic  css=#fieldsetlegend-contact_details
    Click element  id=fieldsetlegend-contact_details
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-phone  10
    Input text  name=form.widgets.IContactDetails.phone  081586100
    Input text  name=form.widgets.IContactDetails.email  contact@imio.be
    Input text  name=form.widgets.IContactDetails.website  www.imio.be
    sleep  ${S_S}
    Add clic  css=#fieldsetlegend-address
    Click element  id=fieldsetlegend-address
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-city  10
    Input text  name=form.widgets.IContactDetails.street  Rue Léon Morel
    Input text  name=form.widgets.IContactDetails.number  1
    Input text  name=form.widgets.IContactDetails.zip_code  5032
    Input text  name=form.widgets.IContactDetails.city  Isnes
    sleep  ${S_S}
    Add clic  css=#pb_2 #form-buttons-save
    Click button  css=#pb_2 #form-buttons-save

    sleep  ${S_S}
    Update element style  css=#oform-widgets-organization-1-wrapper > label  padding-right  1em
    ${note1}  Add pointy note  css=#oform-widgets-organization-1-wrapper > label
    ...  L'organisation est créée et sélectionnée.  position=right  color=blue  width=200
    sleep  ${N_S}
    Remove elements  ${note1}

    # Create sub level
    ${note1}  Add main note  Si nécessaire, on peut créer des sous-niveaux (département, service) dans une organisation nouvellement créée ou dans une organisation déjà existante qu'on a sélectionné.
    Sleep  ${L_S}
    Remove element  id=${note1}

    Add clic  css=#oform-widgets-organization-autocomplete .addnew
    Click element  css=#oform-widgets-organization-autocomplete .addnew
    Wait until element is visible  css=#pb_2 #form-widgets-IBasic-title  10
    Input text  css=#pb_2 #form-widgets-IBasic-title  Département logiciels libres
    Input text  name=form.widgets.enterprise_number  BE0841470248
    sleep  ${S_S}
    Add clic  css=#fieldsetlegend-contact_details
    Click element  id=fieldsetlegend-contact_details
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-phone  10
    Input text  name=form.widgets.IContactDetails.phone  081586114
    Input text  name=form.widgets.IContactDetails.email  dll@imio.be
    Input text  name=form.widgets.IContactDetails.website  www.imio.be
    Add clic  id=fieldsetlegend-address
    Click element  id=fieldsetlegend-address
    Wait until element is visible  id=form-widgets-IContactDetails-use_parent_address-0  10
    # ${note1}  Add pointy note  formfield-form-widgets-IContactDetails-use_parent_address
    # ...  Par défaut, l'adresse parent est utilisée. On peut décocher pour entrer une adresse différente.  position=top  color=blue  width=300
    ${note1}  Add main note  Par défaut, l'adresse parent est utilisée. On peut décocher pour entrer une adresse différente.
    sleep  ${N_S}
    Remove element  ${note1}
    Add clic  css=#pb_2 #form-buttons-save
    Click button  css=#pb_2 #form-buttons-save
    sleep  ${S_S}

    ${note1}  Add pointy note  css=#oform-widgets-organization-2-wrapper > label
    ...  Le sous-niveau créé est sélectionné.  position=right  color=blue  width=200
    sleep  ${N_S}
    Remove elements  ${note1}

    ${note1}  Add pointy note  css=#pb_1 #oform-buttons-cancel
    ...  On peut confirmer la sélection faite ou l'annuler.  position=right  color=blue  width=500
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  css=#pb_1 #oform-buttons-save
    Click element  css=#pb_1 #oform-buttons-save
    Wait until element is visible  css=#form-widgets-sender-0-wrapper  10

    # Create person
    ${main1}  Add main note  On va refaire la même manipulation pour créer une personne.
    Sleep  ${L_S}
    Remove element  id=${main1}

    Add clic  css=.addnew
    Click element  css=.addnew
    sleep  ${S_S}
    Input text  name=oform.widgets.person.widgets.query  Marc Leduc
    Wait until element is visible  css=#oform-widgets-person-autocomplete .addnew  10
    ${note1}  Add pointy note  css=#oform-widgets-person-widgets-query
    ...  Pas de résultat: on va la créer...  position=top  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}

    Add clic  css=#oform-widgets-person-autocomplete .addnew
    Click element  css=#oform-widgets-person-autocomplete .addnew
    ${pb}  set variable  pb_6
    Wait until element is visible  ${pb}  10

    ${note1}  Add main note  Par défaut, les prénom et nom sont repris de la recherche précédente. On complète le reste de la fiche signalétique: tout n'est pas nécessaire ! L'adresse postale et l'adresse email sont importantes afin de savoir répondre...
    Sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add main note  Attention, Ce sont les données privées d'une personne qu'il faut encoder. Pas ses données professionnelles, qui sont à encoder dans le cadre d'une fonction occupée.
    Sleep  ${L_S}
    Remove element  id=${note1}

    # ${note1}  Add pointy note  formfield-form-widgets-gender
    # ...  La sélection du genre est intéressante car elle remplit automatiquement la civilité, qui sera utilisée dans les modèles de document.  position=top  color=blue  width=400
    ${note1}  Add main note  La sélection du genre est intéressante car elle remplit automatiquement la civilité, qui sera utilisée dans les modèles de document.
    Highlight  formfield-form-widgets-gender
    sleep  ${N_S}
    Clear highlight  formfield-form-widgets-gender
    Remove element  id=${note1}
    Add clic  id=form-widgets-gender-0
    Click element  id=form-widgets-gender-0
    sleep  ${N_S}
    Add clic  id=fieldsetlegend-contact_details
    Click element  id=fieldsetlegend-contact_details
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-cell_phone  10
    Input text  name=form.widgets.IContactDetails.cell_phone  0472452345
    Input text  name=form.widgets.IContactDetails.email  marcleduc@hotmail.com
    Add clic  id=fieldsetlegend-address
    Click element  id=fieldsetlegend-address
    Wait until element is visible  id=form-widgets-IContactDetails-number  10
    Input text  name=form.widgets.IContactDetails.street  Rue des Papillons
    Input text  name=form.widgets.IContactDetails.number  25/41
    Input text  name=form.widgets.IContactDetails.zip_code  4020
    Input text  name=form.widgets.IContactDetails.city  Liège
    Sleep  ${S_S}

    Add clic  css=#${pb} #form-buttons-save
    Click button  css=#${pb} #form-buttons-save
    Wait until element is visible  css=#oform-widgets-person-1-wrapper  20
    ${note1}  Add pointy note  css=#oform-widgets-person-1-wrapper
    ...  La personne est créée et sélectionnée.  position=right  color=blue  width=200
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=#pb_1 #oform-buttons-cancel
    ...  On peut confirmer la sélection faite ou l'annuler.  position=right  color=blue  width=500
    sleep  ${S_S}
    Remove element  id=${note1}
    Add clic  css=#pb_1 #oform-buttons-save
    Click element  css=#pb_1 #oform-buttons-save
    sleep  ${S_S}

    # Create function
    ${main1}  Add main note  On va refaire la même manipulation pour créer une fonction occupée par une personne dans une organisation.
    Sleep  ${L_S}
    Remove element  id=${main1}

    Add clic  css=.addnew
    Click element  css=.addnew
    sleep  ${S_S}
    Input text  name=oform.widgets.organization.widgets.query  imio
    Click element  css=#oform-widgets-organization-widgets-query
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    sleep  ${S_S}
    Click element  css=.ac_results:not([style*="display: none"]) li:nth-child(1)

    Input text  name=oform.widgets.person.widgets.query  leduc
    Click element  css=#oform-widgets-person-widgets-query
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    sleep  ${S_S}
    Click element  css=.ac_results:not([style*="display: none"]) li:nth-child(1)

    ${main1}  Add main note  Quand on sélectionne (ou on crée) dans cette fenêtre à la fois une organisation et une personne, des champs supplémentaires apparaissent. Ils permettent de définir une fonction occupée avec des données professionnelles.
    Sleep  ${L_S}
    Sleep  ${S_S}
    Remove element  id=${main1}

    Wait until element is visible  css=#oform-widgets-plone_0_held_position-label  10
    Input text  name=oform.widgets.plone_0_held_position.label  Agent
    sleep  ${S_S}

    # ScrollDown
    ScrollDown
    # Scroll Element Into View  css=#oform #oform-buttons-save

    Add clic  oform-buttons-save
    Click button  id=oform-buttons-save
    ScrollUp
    sleep  ${N_S}

    # Choose person
    ${main1}  Add main note  On a couvert la création de tous les types de contact. On ne va garder que celui qui nous intéresse.
    Sleep  ${L_S}
    Remove element  id=${main1}

    Add clic  form-widgets-sender-0
    Click element  form-widgets-sender-0
    Add clic  form-widgets-sender-2
    Click element  form-widgets-sender-2
    sleep  ${S_S}

    ScrollDown
    sleep  ${S_S}

    ${note1}  Add pointy note  id=form-buttons-cancel
    ...  On peut sauvegarder.  position=right  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=form-buttons-save
    Click element  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10

    ${main1}  Add main note  La création d'un contact peut paraître un peu plus laborieuse, mais elle n'est à faire qu'une seule fois. Il est donc conseillé de le faire correctement.
    Sleep  ${L_S}
    Remove element  id=${main1}

    Add end message

Ajouter une annexe
    # ATTENTION: le pointeur souris doit être hors de la fenêtre !!
    # setup
    [TAGS]  RUN10
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned?redirect=
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
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
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
    # Ajouter une annexe
    ${note1}  Add title  Tutoriel vidéo iA.docs : comment ajouter une annexe...
    Sleep  ${L_S}
    Remove element  id=${note1}

    ${main1}  Add main note  L'action est identique qu'on soit sur une fiche courrier entrant ou sortant.
    Sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(5)
    ...  On va passer par le menu "Ajouter"  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(5)
    Remove element  id=${note1}
    Click element  css=table.actionspanel-no-style-table td:nth-child(5)

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

    ${main1}  Add main note  L'annexe ajoutée est affichée.
    Sleep  ${N_S}
    Remove element  id=${main1}

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

    Add end message

Ajouter une tâche
    # ATTENTION: le pointeur souris doit être hors de la fenêtre !!
    # setup
    [TAGS]  RUN11
    Enable autologin as  encodeur
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Go to  ${PLONE_URL}/import_scanned?redirect=
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
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
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
    # Ajouter une tache
    ${note1}  Add title  Tutoriel vidéo iA.docs : comment ajouter une tâche...
    Sleep  ${L_S}
    Remove element  id=${note1}

    ${main1}  Add main note  L'action est identique qu'on soit sur une fiche courrier entrant, sortant ou une tâche elle-même.
    Sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(5)
    ...  On va passer par le menu "Ajouter"  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(5)
    Remove element  id=${note1}
    Click element  css=table.actionspanel-no-style-table td:nth-child(5)

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(5)
    ...  Et ensuite sélectionner "Tâche"  position=left  color=blue  width=200
    sleep  ${N_S}

    # Vue d'ajout
    GO to  ${PLONE_URL}/incoming-mail/dmsincomingmail/++add++task
    Wait until element is visible  css=body.template-task #formfield-form-widgets-ITask-enquirer  10

    ${main1}  Add main note  On peut compléter le formulaire. Les champs marqués d'un carré rouge sont obligatoires.
    Sleep  ${L_S}
    Remove element  id=${main1}

    Input text  id=form-widgets-title  Ajouter la candidature dans la base de recrutement
    sleep  1

    ${note1}  Add pointy note  css=#form-widgets-ITask-assigned_group  Par défaut, le "groupe assigné" est le même que celui du parent (courrier ou tâche). Il est évidemment possible d'assigner une tâche à un autre service.  position=right  color=blue  width=500
    sleep  ${L_S}
    Remove element  id=${note1}
    # Select From List By Index  id=form-widgets-ITask-assigned_group  2

    ${note1}  Add pointy note  css=#form-widgets-ITask-assigned_user  Si on connaît l'agent traitant, on peut le choisir. Dans le cas contraire, c'est le N+1 qui attribuera (surtout si c'est un autre service).  position=right  color=blue  width=500
    sleep  ${L_S}
    Remove element  id=${note1}

    Select From List By Index  id=form-widgets-ITask-assigned_user  1

    ${note1}  Add pointy note  id=form-buttons-cancel
    ...  Il reste à sauvegarder.  position=right  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=form-buttons-save
    Click element  form-buttons-save
    Wait until element is visible  css=body.template-item_view #formfield-form-widgets-ITask-enquirer  10

    ${main1}  Add main note  La tâche est créée dans la fiche courrier (dans notre exemple) mais pourrait l'être aussi dans une autre tâche.
    Sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=div.viewlet_workflowstate
    ...  L'état actuel est "En création". La tâche reste "privée" donc seulement visible par le groupe proposant actuellement.  position=left  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}


    ${note1}  Add pointy note  css=div.faceted-tagscloud-collection-widget-portlet li:nth-child(12)
    ...  Les états possibles pour les tâches sont montrés dans les recherches commençant par "État".  position=top  color=blue  width=250
    sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=table.actionspanel-no-style-table td:nth-child(2)
    ...  On va "Mettre à faire" pour proposer la tâche.  position=top  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=table.actionspanel-no-style-table td:nth-child(2)
    Remove element  id=${note1}
    Click element  css=table.actionspanel-no-style-table td:nth-child(2)

    ${main1}  Add main note  L'état est maintenant "À faire". Si un utilisateur n'avait pas été sélectionné, l'état serait resté "À assigner" et le N+1 aurait dû intervenir. Sans N+1, la tâche arrive dans le service et les agents doivent choisir de la gérer.
    sleep  ${N_S}
    Sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=#portal-breadcrumbs #breadcrumbs-2
    ...  Pour remonter au parent, on va utiliser le fil d'ariane et cliquer sur le nom du courrier  position=bottom  color=blue  width=300
    sleep  ${L_S}
    Remove element  id=${note1}
    Add clic  css=#portal-breadcrumbs #breadcrumbs-2
    Click element  css=#portal-breadcrumbs #breadcrumbs-2
    Wait until element is visible  css=.DV-pageImage  10
    sleep  ${S_S}

    ScrollDown

    ${note1}  Add pointy note  css=#viewlet-below-content-body>fieldset
    ...  La tâche ajoutée à la fiche courrier est listée dans un tableau en bas de la fiche  position=top  color=blue  width=300
    sleep  ${L_S}
    Remove element  id=${note1}

    ScrollUp

    ${main1}  Add main note  Si une tâche est assignée à un service qui n'avait pas encore de droit sur la fiche (pas service traitant ou pas en copie), ce service obtient automatiquement un droit de visualisation de la fiche courrier, afin de voir le contexte de traitement de sa tâche.
    sleep  ${N_S}
    Sleep  ${L_S}
    Remove element  id=${main1}

    # View tâches
    ${note1}  Add pointy note  id=portaltab-tasks  Un onglet spécifique permet également de lister toutes les tâches.  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=portaltab-tasks
    Click element  id=portaltab-tasks
    Wait until element is visible  css=.faceted-table-results  10

    ${main1}  Add main note  Le tableau de bord des tâches se présente comme celui des courriers entrants ou sortants. Il contient les mêmes fonctionnalités qui sont présentées dans le guide "Naviguer dans l'interface" et dans le guide "Utiliser les recherches".
    sleep  ${N_S}
    Sleep  ${L_S}
    Remove element  id=${main1}

    Add end message

Utiliser les recherches
    # setup
    [TAGS]  RUN12
    Enable autologin as  encodeur
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Go to  ${PLONE_URL}/import_scanned?redirect=
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
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
    GO to  ${PLONE_URL}/
    # start video
    Run keyword if  '${RECORD}'=='1'  Pause
    sleep  ${S_S}
    ${note1}  Add title  Tutoriel vidéo iA.docs : comment utiliser les recherches...
    Sleep  ${L_S}
    Remove element  id=${note1}

    ${main1}  Add main note  Afin de rechercher une fiche courrier ou une tâche, le plus simple est d'utiliser le tableau de bord correspondant.
    sleep  ${L_S}
    Remove element  id=${main1}

    # Filtre simple tableau de bord
    ${note1}  Add pointy note  id=portaltab-incoming-mail
    ...  Par exemple dans les courriers entrants...  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=portaltab-incoming-mail
    Click element  id=portaltab-incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    sleep  ${N_S}

    ${note1}  Add pointy note  css=#c2_widget form
    ...  Ce filtre permet de rechercher une fiche après avoir tapé le début d'un ou plusieurs mots. La recherche s'effectue dans le code-barre, l'intitulé et la description.  position=bottom  color=blue  width=500
    sleep  ${L_S}
    Remove element  id=${note1}

    Input text  id=c2  candid
    sleep  ${S_S}

    ${note1}  Add pointy note  id=c2_button
    ...  Après avoir entré une valeur, il faut soit appuyer sur "Enter", soit cliquer sur la loupe.  position=right  color=blue  width=600
    sleep  ${N_S}
    Add clic  id=c2_button
    Remove element  id=${note1}
    Click element  id=c2_button
    sleep  ${S_S}

    ${main1}  Add main note  Le tableau de bord est alors adapté avec les résultats correspondants.
    sleep  ${N_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  css=#c2_widget form
    ...  Pour affiner le résultat, on peut filtrer sur plusieurs mots de la manière suivante. Les premiers mots (non complets) doivent être suffixés avec une astérisque "*". Pour le dernier mot, elle est implicite.  position=bottom  color=blue  width=500
    Input text  id=c2  candid* post* ouvri
    sleep  ${L_S}
    Add clic  id=c2_button
    Remove element  id=${note1}
    Click element  id=c2_button
    sleep  ${N_S}

    ${note1}  Add pointy note  css=#c2_widget form
    ...  Pour enlever le filtre, il faut effacer la valeur et soumettre à nouveau.  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Input Text  id=c2  ${EMPTY}
    Add clic  id=c2_button
    Remove element  id=${note1}
    sleep  ${N_S}

    ${note1}  Add pointy note  css=#c2_widget form
    ...  Il est possible de filtrer sur plusieurs mots de manière exacte en les entourant par des guillemets.  position=bottom  color=blue  width=300
    Input text  id=c2  "offre d'emploi"
    sleep  ${L_S}
    Add clic  id=c2_button
    Remove element  id=${note1}
    Click element  id=c2_button
    sleep  ${N_S}

    ${note1}  Add pointy note  css=#c2_widget form
    ...  Il est possible aussi de filtrer sur un mot OU un autre en ajoutant le mot "OR" entre les mots.  position=bottom  color=blue  width=300
    Input text  id=c2  offr* OR candidatu
    sleep  ${L_S}
    Add clic  id=c2_button
    Remove element  id=${note1}
    Click element  id=c2_button
    sleep  ${N_S}

    ${note1}  Add pointy note  css=#c2_widget form
    ...  De manière plus élaborée encore, on peut regrouper entre parenthèse plusieurs termes pour les regrouper logiquement.  position=bottom  color=blue  width=300
    Input text  id=c2  (offr* emploi) OR candidatu
    sleep  ${L_S}
    Add clic  id=c2_button
    Remove element  id=${note1}
    Click element  id=c2_button
    sleep  ${N_S}

    ${note1}  Add pointy note  css=#c2_widget form
    ...  Le filtre sur un code-barre est particulier: on peut entrer le code complet (préfixé par IMIO ou non).  position=bottom  color=blue  width=300
    Input text  id=c2  010500000000001
    sleep  ${L_S}
    Add clic  id=c2_button
    Remove element  id=${note1}
    Click element  id=c2_button
    sleep  ${N_S}

    ${note1}  Add pointy note  css=#c2_widget form
    ...  Ou, par facilité, uniquement les chiffres après les zéros...  position=bottom  color=blue  width=300
    Input text  id=c2  1
    sleep  ${N_S}
    Add clic  id=c2_button
    Remove element  id=${note1}
    Click element  id=c2_button
    sleep  ${N_S}

    # filtre avancés
    Clear Element Text  id=c2
    ${note1}  Add pointy note  css=.faceted-sections-buttons-more
    ...  Il est possible d'afficher des filtres avancés.  position=left  color=blue  width=300
    sleep  ${N_S}
    Add clic  css=.faceted-sections-buttons-more
    Remove element  id=${note1}
    Click element  css=.faceted-sections-buttons-more
    sleep  ${N_S}

    ${main1}  Add main note  Les filtres utilisés s'ajoutent toujours à ceux déjà utilisés précédemment. Il y a plusieurs types de filtres:
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  id=c4_widget
    ...  Des filtres "liste de sélection". À chaque sélection le résultat s'adapte.  position=bottom  color=blue  width=300
    sleep  ${L_S}
    Add clic  id=c4_proposed_to_agent
    Click element  id=c4_proposed_to_agent
    Remove element  id=${note1}
    sleep  ${N_S}

    ${note1}  Add pointy note  id=c10_widget
    ...  Des filtres "intervalles de temps". Le résultat s'adapte quand les 2 dates sont sélectionnées.  position=bottom  color=blue  width=300
    sleep  ${L_S}
    ${date}=  Get Current Date  local  exclude_millis=yes
    ${convert}=      Convert Date      ${date}      result_format=%d/%m/%Y
    input text  id=c10-start-input  ${convert}
    input text  id=c10-end-input  ${convert}
    Click element  css=#c4_widget fieldset legend
    Remove element  id=${note1}
    sleep  ${N_S}

    ${note1}  Add pointy note  id=c12_widget
    ...  Des filtres "contact". On cherche le contact, on le sélectionne et on clique sur la loupe. Le terme [TOUT] permet de sélectionner une organisation, ses sous-niveaux et les fonctions occupées associées.  position=right  color=blue  width=400
    sleep  ${L_S}
    Input text  s2id_autogen1  swde
    sleep  ${N_S}
    Input text  s2id_autogen1  leduc
    Add clic  css=#select2-drop li.select2-result.select2-highlighted
    Click element  css=#select2-drop li.select2-result.select2-highlighted
    Add clic  id=c12_button
    # Click element  id=c12_button  deactivated because bug show uid
    Remove element  id=${note1}
    sleep  ${N_S}

    ${note1}  Add pointy note  id=c17_widget
    ...  Des filtres "texte" semblable au premier filtre texte vu précédemment.  position=bottom  color=blue  width=400
    sleep  ${L_S}

    # livesearch
    ${main1}  Add main note  Si on ne trouve pas via un tableau de bord, il est possible de rechercher plus largement en cherchant dans le texte océrisé des courriers scannés, générés ou des emails.
    sleep  ${L_S}
    Remove element  id=${main1}

    ${note1}  Add pointy note  id=portal-logo
    ...  On se remet à la racine de l'outil, juste pour montrer ce lien ;-)  position=right  color=blue  width=500
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=portal-logo
    Click element  id=portal-logo
    sleep  ${N_S}

    ${note1}  Add pointy note  id=livesearch0
    ...  On va utiliser le champ de recherche plus global qui cherche aussi dans les fichiers.  position=bottom  color=blue  width=300
    sleep  ${L_S}
    Remove element  id=${note1}
    Input text  searchGadget  Candidature
    sleep  ${N_S}

    ${note1}  Add pointy note  id=LSResult
    ...  Une recherche instantanée affiche les premiers résultats. On trouve à la fois une fiche courrier entrant mais aussi un fichier. On peut cliquer sur un résultat pour visualiser l'élément.  position=left  color=blue  width=400
    sleep  ${L_S}
    Remove element  id=${note1}
    Add clic  css=#LSResult li.LSRow:nth-child(2)
    Click element  css=#LSResult li.LSRow:nth-child(2)
    Wait until element is visible  form-groups-scan  10
    sleep  ${N_S}

    ${note1}  Add pointy note  id=livesearch0
    ...  Dans la même recherche, si on clique sur la loupe, on arrive sur une vue contextuelle.  position=bottom  color=blue  width=300
    Input text  searchGadget  Candidature
    sleep  ${L_S}
    Remove element  id=${note1}
    Add clic  css=input.searchButton
    Click element  css=input.searchButton
    Wait until element is visible  css=form.searchPage  10
    sleep  ${N_S}

    ${main1}  Add main note  On retrouve le fichier, contextualisé par la fiche auquel il est rattaché.
    sleep  ${L_S}
    Remove element  id=${main1}

    Add end message

Gérer les modèles
# partie guide utilisation : Gérer les modèles


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
    Go to  ${PLONE_URL}/video_doc_init?pdb=
    Disable autologin
    # Register Keyword To Run On Failure  debug
    Run keyword if  '${RECORD}'=='0'  Set suite variable  \${L_S}  2
    Run keyword if  '${RECORD}'=='0'  Set suite variable  \${N_S}  1
    Run keyword if  '${RECORD}'=='0'  Set suite variable  \${S_S}  1
    Run keyword if  '${RECORD}'=='0'  Set suite variable  \${C_S}  0.5
