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
# setup
    [TAGS]  RUN1
    Enable autologin as  encodeur
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

    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Go to  ${PLONE_URL}/
# start video
    Pause
# bandeau principal
    ${main1}  Add title  Tutoriel vidéo iA.docs : Naviguer dans l'interface...
    sleep  ${N_S}
    Remove element  ${main1}
    Highlight  id=portal-globalnav
    ${note1}  Add main note  Le bandeau principal permet un accès rapide aux fonctionnalités : entrant, sortant, gestion des tâches, annuaire de contact et gestion des modèles sortants.
    sleep  ${L_S}
    Remove element  id=${note1}
    Clear Highlight  id=portal-globalnav
    ${note1}  Add pointy note  id=portaltab-incoming-mail  Afficher le courrier entrant.  position=bottom  color=blue
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=portaltab-incoming-mail
# interface courrier entrant
    Click element  id=portaltab-incoming-mail
    Highlight  css=.portlet.portletWidgetCollection
    ${note1}  Add pointy note  css=.portlet.portletWidgetCollection  Les tableaux de bords affichent les courriers par catégorie.  position=right  color=blue
    sleep  ${N_S}
    Remove element  id=${note1}

    ${note1}  Add pointy note  css=.portlet.portletWidgetCollection  Il est possible de filtrer sur les courriers à traiter, en cours, dans le service, en copie, etc.  position=right  color=blue
    sleep  ${N_S}
    Remove element  id=${note1}
    Clear Highlight  css=.portlet.portletWidgetCollection
    Highlight  id=faceted_table
    ${note2}  Add pointy note  id=faceted_table  Les courriers sont affichés ligne par ligne, avec les informations clés.  position=top  color=blue
    sleep  ${N_S}
    Clear Highlight  id=faceted_table
    Remove element  id=${note2}

    Highlight  css=.th_header_due_date
    ${note2}  Add pointy note  css=.th_header_due_date  Il est possible de trier par colonne, par exemple avec la date d'échéance.  position=top  color=blue
    sleep  ${N_S}
    Clear Highlight  css=.th_header_due_date
    Remove element  id=${note2}

    Highlight  css=.th_header_actions
    ${note2}  Add pointy note  css=.th_header_actions  La colonne "Actions" permet un accès rapide aux actions d'une fiche courrier.  position=top  color=blue
    sleep  ${N_S}
    Clear Highlight  css=.th_header_actions
    Remove element  id=${note2}

    Highlight  id=batch-actions
    ${note2}  Add pointy note  id=batch-actions  Les actions par lot effectuent des actions sur tous les courriers sélectionnés dans la première colonne au préalable.  position=top  color=blue
    sleep  ${L_S}
    Clear Highlight  id=batch-actions
    Remove element  id=${note2}

    Highlight  id=faceted-center-column
    ${note2}  Add pointy note  id=faceted-center-column  La zone de recherche permet de retrouver les courriers du tableau de bord.  position=bottom  color=blue
    sleep  ${N_S}
    Clear Highlight  id=faceted-center-column
    Remove element  id=${note2}

    Highlight  css=.LSBox
    ${note2}  Add pointy note  css=.LSBox  Une recherche plus globale permet de rechercher dans le texte océrisé des courriers.  position=bottom  color=blue
    sleep  ${N_S}
    Clear Highlight  css=.LSBox
    Remove element  id=${note2}

    ${note1}  Add main note  Les recherches sont expliquées plus en détail dans le guide "Comment utiliser les recherches".
    sleep  ${L_S}
    Remove element  id=${note1}

    Highlight  id=breadcrumbs-you-are-here
    ${note2}  Add pointy note  id=breadcrumbs-you-are-here  Le fil d'ariane permet de se situer et de revenir au niveau du dessus à tout moment.  position=bottom  color=blue
    sleep  ${N_S}
    Clear Highlight  id=breadcrumbs-you-are-here
    Remove element  id=${note2}

    Add end message

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
#    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
#    Wait until element is visible  css=.DV-pageImage  10

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
    [TAGS]  RUN1
    Enable autologin as  encodeur
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
    [TAGS]  RUN1
    Set Window Size  ${W_WIDTH}  ${W_HEIGHT}
    Enable autologin as  agent
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25  additional_address_details=41  email=marcleduc@hotmail.com  cell_phone=04724523453
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  css=div.table_faceted_results  10
    # start video
    pause
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


Transférer un email entrant
# partie guide utilisation : Transférer un email entrant


Envoyer un email sortant
# setup
    [TAGS]  RUN1
    Enable autologin as  encodeur
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
#    pause
# visualisation répondre

    ${main1}  Add title  Tutoriel vidéo iA.docs : comment envoyer un email sortant...
    sleep  ${L_S}
    Remove element  id=${main1}

    debug
    Add end message

Valider un courrier entrant
# partie guide utilisation : Valider un courrier entrant


Ajouter un contact
# partie guide utilisation : Ajouter un contact


Ajouter une annexe
# ATTENTION: le pointeur souris doit être hors de la fenêtre !!
# setup
    [TAGS]  RUN1
    Enable autologin as  encodeur
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

    Add end message

Ajouter une tâche
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
    # Ajouter une tache
    ${note1}  Add title  Tutoriel vidéo iA.docs : comment ajouter une tâche...
    Sleep  ${L_S}
    Remove element  id=${note1}

    ${note1}  Add main note  L'action est identique qu'on soit sur une fiche courrier entrant, sortant ou une tâche elle-même.
    Sleep  ${L_S}
    Remove element  id=${note1}

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

    ${note1}  Add main note  On peut compléter le formulaire. Les champs marqués d'un carré rouge sont obligatoires.
    Sleep  ${L_S}
    Remove element  id=${note1}

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

    ${note1}  Add main note  La tâche est créée dans la fiche courrier (dans notre exemple) mais pourrait l'être aussi dans une autre tâche.
    Sleep  ${L_S}
    Remove element  id=${note1}

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

    ${note1}  Add main note  L'état est maintenant "À faire". Si un utilisateur n'avait pas été sélectionné, l'état serait resté "À assigner" et le N+1 aurait dû intervenir. Sans N+1, la tâche arrive dans le service et les agents doivent choisir de la gérer.
    sleep  ${N_S}
    Sleep  ${L_S}
    Remove element  id=${note1}

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

    ${note1}  Add main note  Si une tâche est assignée à un service qui n'avait pas encore de droit sur la fiche (pas service traitant ou pas en copie), ce service obtient automatiquement un droit de visualisation de la fiche courrier, afin de voir le contexte de traitement de sa tâche.
    sleep  ${N_S}
    Sleep  ${L_S}
    Remove element  id=${note1}

    # View tâches
    ${note1}  Add pointy note  id=portaltab-tasks  Un onglet spécifique permet également de lister toutes les tâches.  position=bottom  color=blue  width=300
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=portaltab-tasks
    Click element  id=portaltab-tasks
    Wait until element is visible  css=.faceted-table-results  10

    ${note1}  Add main note  Le tableau de bord des tâches se présente comme celui des courriers entrants ou sortants. Il contient les mêmes fonctionnalités qui sont présentées dans le guide "Naviguer dans l'interface" et dans le guide "Utiliser les recherches".
    sleep  ${N_S}
    Sleep  ${L_S}
    Remove element  id=${note1}

    Add end message

Utiliser les recherches
# partie guide utilisation : Utiliser les recherches
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
    GO to  ${PLONE_URL}/
#    Go to  ${PLONE_URL}/incoming-mail
#    Wait until element is visible  css=.faceted-table-results  10
#    Select collection  incoming-mail/mail-searches/to_treat
# start video
    #pause
# Recherche globale
    ${note1}  Add title  Tutoriel vidéo iA.docs : comment utiliser les recherches...
    Sleep  ${L_S}
    Remove element  id=${note1}

    ${main1}  Add main note  Afin de rechercher une fiche courrier ou une tâche, le plus simple est d'utiliser le tableau de bord correspondant.
    sleep  ${L_S}
    Remove element  id=${main1}

    # Recherche par tableau de bord
    ${note1}  Add pointy note  id=portaltab-incoming-mail
    ...  Par exemple dans les courriers entrants...  position=bottom  color=blue  width=200
    sleep  ${N_S}
    Remove element  id=${note1}
    Add clic  id=portaltab-incoming-mail
    Click element  id=portaltab-incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    sleep  ${N_S}

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
    Disable autologin
