*** Settings ***
Resource  plone/app/robotframework/keywords.robot
Resource  plone/app/robotframework/selenium.robot
Resource  common.robot

Library  Remote  ${PLONE_URL}/RobotRemote
Library  plone.app.robotframework.keywords.Debugging
Library  Selenium2Screenshots

Suite Setup  Suite Setup
Suite Teardown  Close all browsers

*** Variables ***

#${BROWSER} =  GoogleChrome
${SELENIUM_RUN_ON_FAILURE} =  Debug

*** Test cases ***

Premiers pas
# partie 2.1 Premiers pas
    #Log to console  LOG
    Go to  ${PLONE_URL}
    Capture and crop page screenshot  doc/utilisation/2-1 accès à l'application.png  css=.site-plone  id=portal-footer-wrapper
    Enable autologin as  encodeur
    #Log in  encodeur  Dmsmail69!
    Go to  ${PLONE_URL}
    Capture and crop page screenshot  doc/utilisation/2-1 page d'accueil.png  css=.site-plone  id=portal-footer-wrapper
    Capture and crop page screenshot  doc/utilisation/2-1 fil d'ariane.png  id=breadcrumbs-you-are-here  id=breadcrumbs-home

CE depuis le scanner
# partie 2.2.1 Envoi par le scanner
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/utilisation/2-2-1 onglet courrier entrant.png  css=.site-plone  id=portal-footer-wrapper
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/lock-unlock
    Wait until element is visible  css=.DV-pageImage  10
    Select collection  incoming-mail/mail-searches/searchfor_created
    Capture and crop page screenshot  doc/utilisation/2-2-1 recherche en création.png  css=.site-plone  id=portal-footer-wrapper  id=faceted-results
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/lock-unlock?unlock=1
    Wait until element is visible  css=.DV-pageImage  10

    ### Edit mail
    Capture and crop page screenshot  doc/utilisation/2-2-1 lien modifier courrier.png  id=contentview-edit  id=content-history  css=table.actionspanel-no-style-table
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-2-1 édition courrier.png  css=.documentEditable
    Click element  css=.DV-textView span.DV-trigger
    #Highlight  css=.DV-textView
    ${note1}  Add pointy note  css=.DV-textView  Onglet texte  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-1 édition texte océrisé.png  id=portal-columns  ${note1}
    #Clear highlight  css=.DV-textView
    Remove element  id=${note1}
    Input text  name=form.widgets.IDublinCore.title  Candidature à un poste d'ouvrier communal
    Input text  name=form.widgets.IDublinCore.description  Lettre de candidature spontanée

    ### Sender field
    Input text  name=form.widgets.sender.widgets.query  le
    Sleep  0.5
    Wait until element is visible  css=.ac_results  10
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur recherche le.png  id=fieldset-default
    Click element  id=form-widgets-external_reference_no
    Wait until element is not visible  css=.ac_results  10
    Input text  name=form.widgets.sender.widgets.query  leduc

    ### Create contact
    ${note2}  Add pointy note  css=.addnew  Lien nouveau contact  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur recherche leduc.png  id=formfield-form-widgets-IDublinCore-description  ${note2}  id=formfield-form-widgets-original_mail_date
    Remove element  id=${note2}
    Click element  css=.addnew
    Wait until element is visible  css=.overlay-contact-addnew  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 0 création.png  css=.overlay-contact-addnew

    ### Create organization
    Input text  name=oform.widgets.organization.widgets.query  IMIO
    Wait until element is visible  css=#oform-widgets-organization-autocomplete .addnew  10
    Update element style  css=#oform-widgets-organization-autocomplete .addnew  padding-right  1em
    ${note3}  Add pointy note  css=#oform-widgets-organization-autocomplete .addnew  Lien nouvelle organisation  position=right  color=blue
    #Highlight  css=#oform-widgets-organization-autocomplete .addnew
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 1 création lien organisation.png  css=.overlay-contact-addnew  ${note3}
    Remove element  id=${note3}
    #Clear highlight  css=#oform-widgets-organization-autocomplete .addnew
    Click element  css=#oform-widgets-organization-autocomplete .addnew
    Wait until element is visible  id=pb_2  10
    Update element style  id=formfield-form-widgets-activity  display  none
    Select from list by value  id=form-widgets-organization_type  sa
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 1 création organisation.png  id=pb_2
    Click element  id=fieldsetlegend-contact_details
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-phone  10
    Input text  name=form.widgets.IContactDetails.phone  +3265329670
    Input text  name=form.widgets.IContactDetails.email  contact@imio.be
    Input text  name=form.widgets.IContactDetails.website  www.imio.be
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 1 création organisation details.png  id=pb_2
    Click element  id=fieldsetlegend-address
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-city  10
    Input text  name=form.widgets.IContactDetails.number  2
    Input text  name=form.widgets.IContactDetails.street  Avenue Thomas Edison
    Input text  name=form.widgets.IContactDetails.zip_code  7000
    Input text  name=form.widgets.IContactDetails.city  Mons
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 1 création organisation adresse.png  id=pb_2
    Click button  css=#pb_2 #form-buttons-save
    Sleep  1
    Update element style  css=#oform-widgets-organization-1-wrapper > label  padding-right  1em
    ${note4}  Add pointy note  css=#oform-widgets-organization-1-wrapper > label  Organisation créée et sélectionnée  position=right  color=blue
    #Update element style  css=#oform-widgets-organization-autocomplete .addnew  padding-right  1em
    ${note5}  Add pointy note  css=#oform-widgets-organization-autocomplete .addnew  Lien de création d'un sous-niveau  position=right  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 1 création organisation finie.png  id=pb_1  ${note4}  ${note5}
    Remove elements  ${note4}  ${note5}

    ### Create sub level
    Click element  css=#oform-widgets-organization-autocomplete .addnew
    Wait until element is visible  css=#pb_2 #form-widgets-IBasic-title  10
    Input text  css=#pb_2 #form-widgets-IBasic-title  Département logiciels libres
    Click element  id=fieldsetlegend-contact_details
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-phone  10
    Input text  name=form.widgets.IContactDetails.phone  +3265329677
    Input text  name=form.widgets.IContactDetails.email  dll@imio.be
    Input text  name=form.widgets.IContactDetails.website  www.imio.be
    Click element  id=fieldsetlegend-address
    Wait until element is visible  id=form-widgets-IContactDetails-use_parent_address-0  10
    Unselect checkbox  id=form-widgets-IContactDetails-use_parent_address-0
    Input text  name=form.widgets.IContactDetails.number  34
    Input text  name=form.widgets.IContactDetails.street  Zoning Industriel
    Input text  name=form.widgets.IContactDetails.zip_code  5190
    Input text  name=form.widgets.IContactDetails.city  Mornimont
    Click button  css=#pb_2 #form-buttons-save
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 1 création sous orga finie.png  id=pb_1

    ### Create person
    Click element  css=#pb_1 .close
    Wait until element is visible  css=.addnew  10
    Sleep  1
    Click element  css=.addnew
    Sleep  2
    Input text  name=oform.widgets.person.widgets.query  Marc Leduc
    Wait until element is visible  css=#oform-widgets-person-autocomplete .addnew  10
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 2 création lien personne.png  css=.overlay-contact-addnew
    Click element  css=#oform-widgets-person-autocomplete .addnew
    Wait until element is visible  id=pb_6  10
    #Input text  name=form.widgets.firstname  Marc
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 2 création personne.png  id=pb_6
    Click element  id=fieldsetlegend-contact_details
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-cell_phone  10
    Input text  name=form.widgets.IContactDetails.cell_phone  +32472452345
    Input text  name=form.widgets.IContactDetails.email  marcleduc@hotmail.com
    Click element  id=fieldsetlegend-address
    Wait until element is visible  id=form-widgets-IContactDetails-number  10
    Input text  name=form.widgets.IContactDetails.number  25
    Input text  name=form.widgets.IContactDetails.additional_address_details  41
    Input text  name=form.widgets.IContactDetails.street  Rue des Papillons
    Input text  name=form.widgets.IContactDetails.zip_code  4020
    Input text  name=form.widgets.IContactDetails.city  Liège
    Click button  css=#pb_6 #form-buttons-save
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 2 création personne finie.png  id=pb_1

    ### Create function
    Input text  name=oform.widgets.organization.widgets.query  IMIO
    Wait until element is visible  css=.ac_results[style*="display: block"]  10
    Click element  css=.ac_results[style*="display: block"] li:nth-child(2)
    Wait until element is visible  css=#formfield-oform-widgets-plone_0_held_position-label input  10
    Update element style  css=.pb-ajax  max-height  800px !important
    Update element style  id=pb_1  top  30px ! important
    Input text  name=oform.widgets.plone_0_held_position.label  Directeur
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 3 création fonction finie.png  id=pb_1
    Click element  css=#pb_1 .close
    #Click button  id=oform-buttons-save
    Sleep  1

    ### Choose person
    Input text  name=form.widgets.sender.widgets.query  ledu
    Wait until element is visible  css=.ac_results[style*="display: block"]  10
    Click element  css=.ac_results[style*="display: block"] li
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 0 fini.png  id=formfield-form-widgets-IDublinCore-description  id=formfield-form-widgets-original_mail_date

    ### Complete last fields
    Click element  css=.DV-documentView span.DV-trigger
    Select from list by value  id=form-widgets-original_mail_date-day  6
    Select from list by value  id=form-widgets-original_mail_date-month  6
    Select from list by value  id=form-widgets-original_mail_date-year  2012
    Select from list by index  id=form-widgets-treating_groups  2
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-2-1 édition courrier fini.png  css=.documentEditable
    Click button  id=form-buttons-save
    Sleep  2

CE manuel
# partie 2.2.2 Ajout manuel d'une fiche
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10

    ### Create incomingmail
    ${note10}  Add pointy note  css=#newIMCreation  Lien d'ajout  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-2 courrier 1 lien ajout.png  id=portal-column-one  ${note10}
    Remove element  id=${note10}
    Click element  newIMCreation
    Wait until element is visible  css=.template-dmsincomingmail #formfield-form-widgets-sender  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-2-2 courrier 1 création.png  id=content
    Input text  name=form.widgets.IDublinCore.title  Lettre de demande de stage
    Input text  name=form.widgets.sender.widgets.query  Non encod
    Wait until element is visible  css=.ac_results[style*="display: block"]  10
    Click element  css=.ac_results[style*="display: block"] li
    Select from list by value  id=form-widgets-mail_type  courrier
    Select from list by index  id=form-widgets-treating_groups  2
    Click button  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Capture and crop page screenshot  doc/utilisation/2-2-2 courrier 1 création finie.png  id=content  id=viewlet-below-content

    ### Create mainfile
    Update element style  css=#viewlet-above-content-title select[name="Add element"]  padding-right  1em
    ${note11}  Add pointy note  css=#viewlet-above-content-title select[name="Add element"]  Menu ajout d'un élément  position=right  color=blue
    Click element  name=Add element
    # La capture du menu ouvert ne fonctionne pas
    Capture and crop page screenshot  doc/utilisation/2-2-2 ged 1 lien ajout.png  id=parent-fieldname-title  ${note11}
    Remove element  id=${note11}
    Click element  css=#formfield-form-widgets-sender label
    Select from list by label  name=Add element  Fichier ged
    Wait until element is visible  id=formfield-form-widgets-file  10
    Capture and crop page screenshot  doc/utilisation/2-2-2 ged 1 création.png  id=content
    Click element  id=fieldsetlegend-scan
    Wait until element is visible  id=formfield-form-widgets-IScanFields-scan_id  10
    Capture and crop page screenshot  doc/utilisation/2-2-2 ged 1 création scan.png  id=content
    Click button  id=form-buttons-cancel
    Go to  ${PLONE_URL}/incoming-mail/lettre-de-demande-de-stage/create_main_file?filename=60.PDF
    Wait until element is visible  css=.DV-pageImage  10
    ${note12}  Add pointy note  id=breadcrumbs-2  Cliquez ici pour revenir au courrier  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-2 ged 1 création finie.png  id=portal-column-content  ${note12}
    Remove element  id=${note12}
    Go to  ${PLONE_URL}/incoming-mail/lettre-de-demande-de-stage
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-2-2 courrier 2 visualisation.png  id=content

CS en réponse
# partie 2.3.1 Réponse à un courrier entrant
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    Fire transition  ${UID}  propose_to_service_chief
    Enable autologin as  dirg
    ${SENDER} =  Path to uid  /${PLONE_SITE_ID}/contacts/jeancourant
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    ${DF} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-financiere
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  sender  ${SENDER}  reference
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  recipient_groups  ['${DF}']  list
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  external_reference_no  2017/ESB/00123  str
    Fire transition  ${UID}  propose_to_agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10
    ${note60}  Add pointy note  css=#viewlet-above-content-title .apButtonAction_reply  Bouton de réponse  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-1 cs 1 lien répondre.png  id=viewlet-above-content-body  ${note60}
    Remove element  id=${note60}
    Click button  css=#viewlet-above-content-title .apButtonAction_reply
    Wait until element is visible  css=.template-reply #formfield-form-widgets-ITask-due_date  10
    Capture and crop page screenshot  doc/utilisation/2-3-1 cs 1 édition réponse.png  id=content
    Click button  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Capture and crop page screenshot  doc/utilisation/2-3-1 cs 1 édition réponse finie.png  id=content

    ### Create mainfile
    #Update element style  css=#viewlet-above-content-title select[name="Add element"]  padding-right  1em
    ${note61}  Add pointy note  css=#viewlet-above-content-title select[name="Add element"]  Menu ajout d'un élément  position=right  color=blue
    Click element  name=Add element
    # La capture du menu ouvert ne fonctionne pas
    Capture and crop page screenshot  doc/utilisation/2-3-1 cs 2 ged lien ajout.png  id=parent-fieldname-title  ${note61}
    Remove element  id=${note61}
    Click element  css=#formfield-form-widgets-sender label
    Select from list by label  name=Add element  Fichier ged
    Wait until element is visible  id=formfield-form-widgets-file  10
    Capture and crop page screenshot  doc/utilisation/2-3-1 cs 2 ged ajout.png  id=content
    Click button  id=form-buttons-cancel
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature-a-un-poste-douvrier-communal/create_main_file?filename=Réponse+candidature+ouvrier+communal.odt&title=Réponse+candidature+ouvrier+communal
    Wait until element is visible  css=.DV-pageImage  10
    ${note62}  Add pointy note  id=breadcrumbs-2  Cliquez ici pour revenir au courrier  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-1 cs 2 ged ajout fini.png  id=portal-column-content  ${note62}
    Remove element  id=${note62}
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature-a-un-poste-douvrier-communal
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-1 cs 2 visualisation.png  id=content

CS nouveau
# partie 2.3.2 Nouveau courrier sortant
    Enable autologin as  agent
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  css=.faceted-table-results  10

    ### Create outgoingmail
    ${note1}  Add pointy note  id=newOMCreation  Lien d'ajout  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-2 cs 1 lien ajout.png  id=portal-column-one  ${note1}
    Remove element  id=${note1}
    Click element  newOMCreation
    Wait until element is visible  css=.template-dmsoutgoingmail #formfield-form-widgets-sender  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-3-2 cs 1 création.png  id=content
    Input text  name=form.widgets.IDublinCore.title  Annonce de la réfection des trottoirs Rue Moyenne
    Input text  name=form.widgets.recipients.widgets.query  Non encod
    Wait until element is visible  css=.ac_results[style*="display: block"]  10
    Click element  css=.ac_results[style*="display: block"] li
    Click button  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Capture and crop page screenshot  doc/utilisation/2-3-2 cs 1 création finie.png  id=content  id=viewlet-below-content
    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-moyenne/create_main_file?filename=Réfection+trottoir.odt&title=Réfection+trottoir
    Wait until element is visible  css=.DV-pageImage  10
    Go to  ${PLONE_URL}/outgoing-mail/annonce-de-la-refection-des-trottoirs-rue-moyenne
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-2 cs 2 visualisation.png  id=content

CS depuis le scanner
# partie 2.3.3 Envoi par le scanner
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned2
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/utilisation/2-3-3 cs onglet courrier sortant.png  css=.site-plone  id=portal-footer-wrapper
    Go to  ${PLONE_URL}/outgoing-mail/dmsoutgoingmail/lock-unlock
    Wait until element is visible  css=.DV-pageImage  10
    Select collection  outgoing-mail/mail-searches/searchfor_scanned
    Capture and crop page screenshot  doc/utilisation/2-3-3 cs recherche scanné.png  css=.site-plone  id=portal-footer-wrapper  id=faceted-results
    Go to  ${PLONE_URL}/outgoing-mail/dmsoutgoingmail/lock-unlock?unlock=1
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10

    ### Edit mail
    Capture and crop page screenshot  doc/utilisation/2-3-3 cs lien modifier courrier.png  id=contentview-edit  id=content-history  css=table.actionspanel-no-style-table
    Go to  ${PLONE_URL}/outgoing-mail/dmsoutgoingmail/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-3 cs édition courrier.png  css=.documentEditable
    Click element  css=.DV-textView span.DV-trigger
    ${note1}  Add pointy note  css=.DV-textView  Onglet texte  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-3 cs édition texte océrisé.png  id=portal-columns  ${note1}
    Remove element  id=${note1}
    Input text  name=form.widgets.IDublinCore.title  Accusé de réception population
    Select from list by index  id=form-widgets-treating_groups  1
    Click element  form_widgets_sender_select_chzn
    Input text  css=.chzn-search input  agent
    Click element  css=.chzn-results #form_widgets_sender_select_chzn_o_1
    Input text  name=form.widgets.recipients.widgets.query  Bernard
    Wait until element is visible  css=.ac_results[style*="display: block"]  10
    Click element  css=.ac_results[style*="display: block"] li:first-of-type
    Sleep  0.5
    Click element  css=input#form-widgets-external_reference_no
    Click button  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-3-3 cs création finie.png  id=content  id=viewlet-below-content

Menu courrier
# partie 2.4.1 Menu de recherches prédéfinies
    Enable autologin as  Manager
    Set autologin username  dirg
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/utilisation/2-4-1 menu ce.png  css=.portletWidgetCollection
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/utilisation/2-4-1 menu cs.png  css=.portletWidgetCollection
    Go to  ${PLONE_URL}/tasks
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/utilisation/2-4-1 menu tâches.png  css=.portletWidgetCollection

Tableaux de bord
# partie 2.4.2 Tableaux de bord
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned?number=16
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/lock-unlock
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail-1
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  task_description  <p>Fais ceci</p>  text/html
    Fire transition  ${UID}  propose_to_service_chief
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/utilisation/2-4-2 tableaux de bord général.png  id=content
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/lock-unlock?unlock=1
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Unselect checkbox  select_unselect_items
    # treating group
    ${UID2} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    Select checkbox  css=td.select_item_checkbox input[value='${UID2}']
    Click button  id=treatinggroup-batch-action-but
    Wait until element is visible  css=.pb-ajax #formfield-form-widgets-treating_group  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-4-2 tableaux de bord lot choix service.png  css=.pb-ajax
    Click element  css=div.overlay-ajax .close
    # review_state
    Select checkbox  css=td.select_item_checkbox input[value='${UID}']
    Click button  id=transition-batch-action-but
    Wait until element is visible  css=.pb-ajax #formfield-form-widgets-transition  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-4-2 tableaux de bord lot transition.png  css=.pb-ajax
    Click element  css=div.overlay-ajax .close
    Unselect checkbox  css=td.select_item_checkbox input[value='${UID}']
    # recipients
    Click button  id=recipientgroup-batch-action-but
    Wait until element is visible  id=formfield-form-widgets-action_choice  10
    Select from list by value  id=form-widgets-action_choice  replace
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-4-2 tableaux de bord lot services en copie.png  css=.pb-ajax
    Click element  css=div.overlay-ajax .close
    Wait until element is visible  css=.faceted-sections-buttons-more  10
    Click element  css=.faceted-sections-buttons-more
    Wait until element is visible  id=top---advanced---widgets  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-4-2 tableaux de bord filtres avances.png  id=top---advanced---widgets
    click element  css=.select2-container
    Input text  css=.select2-input  elec
    Wait until element is visible  css=.select2-results  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-4-2 tableaux de bord filtre expéditeur.png  id=top---advanced---widgets  css=.select2-results

Visualisation
# partie 2.5 Visualisation des courriers
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25  additional_address_details=41  email=marcleduc@hotmail.com  cell_phone=+324724523453
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  description  Candidature spontanée  str
    Set field value  ${UID}  sender  ${SENDER}  reference
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  original_mail_date  20170314  date
    #Set field value  ${UID}  reception_date  201703121515  datetime%Y%m%d%H%M
    #Fire transition  ${UID}  propose_to_service_chief
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-5 onglet courrier entrant.png  css=.site-plone  id=portal-footer-wrapper
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-5 courrier entrant.png  css=.site-plone  id=portal-footer-wrapper
    # DO NOT WORK ANYMORE: WAITING FOR GECKODRIVER UPDATE !!!!!
    #Mouse over  css=#form-widgets-sender a.link-tooltip
    #Wait until element is visible  css=div.tooltip #person  10
    ## Le pointeur fait disparaître le tooltip
    ##${pointer}  Add pointer  css=#form-widgets-sender a.link-tooltip
    Capture and crop page screenshot  doc/utilisation/2-5 courrier entrant personne.png  id=content
    ##Remove element  ${pointer}
    ## La capture du tooltip title ne fonctionne pas!
    #Mouse over  css=a.version-link
    ##Sleep  1
    ##Capture and crop page screenshot  doc/utilisation/2-5 courrier entrant ged.png  id=content

Modification
# partie 2.6 Modification des courriers
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25  additional_address_details=41  email=marcleduc@hotmail.com  cell_phone=+324724523453
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  description  Candidature spontanée  str
    Set field value  ${UID}  sender  ${SENDER}  reference
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  original_mail_date  20170314  date
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10
    ${note20}  Add pointy note  id=contentview-edit  Lien d'édition  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-6 lien modifier courrier.png  id=contentview-edit  id=content-history  css=table.actionspanel-no-style-table  ${note20}
    Remove element  id=${note20}
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Sleep  0.2
    Capture and crop page screenshot  doc/utilisation/2-6 édition courrier.png  css=.documentEditable
    Click button  id=form-buttons-cancel
    Fire transition  ${UID}  propose_to_service_chief
    Enable autologin as  chef
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-6 édition limitée courrier.png  css=.documentEditable
    Click button  id=form-buttons-cancel

Tâche
# partie 2.7.1 Ajout d'une tâche
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25  additional_address_details=41  email=marcleduc@hotmail.com  cell_phone=+324724523453
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  description  Candidature spontanée  str
    Set field value  ${UID}  sender  ${SENDER}  reference
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  original_mail_date  20170314  date
    Fire transition  ${UID}  propose_to_manager
    Enable autologin as  dirg
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10
    Sleep  0.5
    Select from list by label  name=Add element  Tâche
    Sleep  0.5
    Wait until element is visible  id=formfield-form-widgets-ITask-assigned_group  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-7-1 tache ajout vierge.png  id=content
    Sleep  0.2
    Input text  name=form.widgets.title  Placer le CV dans notre référentiel
    #Input text  css=#formfield-form-widgets-ITask-task_description #content  TEST
    #Select from list by index  name=form.widgets.ITask.assigned_user:list  1
    Click button  id=form-buttons-save
    Wait until element is visible  css=.template-item_view.portaltype-task #formfield-form-widgets-ITask-due_date  10
    Capture and crop page screenshot  doc/utilisation/2-7-1 tache ajout complete.png  id=content
    ${TUID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail/placer-le-cv-dans-notre-referentiel
    Fire transition  ${TUID}  do_to_assign
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/placer-le-cv-dans-notre-referentiel
    Wait until element is visible  css=#plone-contentmenu-workflow span.state-to_assign  10
    Capture and crop page screenshot  doc/utilisation/2-7-1 tache ajout to assign.png  id=content
# partie 2.7.2 Visualisation d'une tâche
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-7-2 tache dans courrier.png  id=content
    Go to  ${PLONE_URL}/tasks
    Wait until element is visible  css=.faceted-table-results  10
    Wait until element is visible  css=.th_header_assigned_group  10
    Capture and crop page screenshot  doc/utilisation/2-7-2 tache dans tableau.png  id=content

Workflow ce
# partie 2.8.1 Principe et utilisation
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/incoming-mail/dmsincomingmail
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25  additional_address_details=41  email=marcleduc@hotmail.com  cell_phone=+324724523453
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  sender  ${SENDER}  reference
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  original_mail_date  20170314  date
    # db
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    ${note1}  Add pointy note  css=.faceted-table-results tr:nth-child(2) td.td_cell_actions td:first-of-type  Transition  position=top  color=blue
    ${note2}  Add pointy note  transition-batch-action  Transition par lot  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-8-1 transition tb.png  css=.faceted-table-results > thead  transition-batch-action  recipientgroup-batch-action  ${note2}
    Remove elements  id=${note1}  id=${note2}
    # ce
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2 état en création.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    ${note30}  Add pointy note  css=input.apButtonWF_propose_to_manager  Transition  position=top  color=blue
    ${note31}  Add pointy note  css=input.apButtonWF_propose_to_service_chief  Transition  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-8-1 bouton transition.png  id=contentview-view  id=content-history  css=table.actionspanel-no-style-table  ${note30}
    Remove elements  id=${note30}  id=${note31}
# partie 2.8.2 ce
    Fire transition  ${UID}  propose_to_manager
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2 transition vers dg.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Enable autologin as  dirg
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2 état dg.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  propose_to_service_chief
    Enable autologin as  chef
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    ${note32}  Add pointy note  css=#formfield-form-widgets-ITask-assigned_user .formHelp  Avertissement  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-8-2 état chef.png  css=.documentEditable
    Remove element  id=${note32}
    Sleep  0.1
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2 édition limitée courrier.png  css=.documentEditable
    Select from list by value  id=form-widgets-ITask-due_date-day  6
    Select from list by value  id=form-widgets-ITask-due_date-month  6
    Select from list by value  id=form-widgets-ITask-due_date-year  2015
    Click button  id=form-buttons-save
    Set field value  ${UID}  assigned_user  agent  field_type normal
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2 état chef assigné.png  css=.documentEditable
    Fire transition  ${UID}  propose_to_agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2 état agent à traiter.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  treat
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2 état agent traitement.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  close
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2 état agent clôturé.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    # back & history
    Click button  css=input.apButtonWF_back_to_treatment
    Wait until element is visible  css=form#confirmTransitionForm  10
    Input text  name=comment  Réouverture pour apporter une réponse complémentaire.\nSuite à un appel téléphonique.
    Capture and crop page screenshot  doc/utilisation/2-8-1 transition retour.png  id=content
    Click button  name=form.buttons.save
    Wait until element is visible  css=.highlight-history-link  10
    Capture and crop page screenshot  doc/utilisation/2-8-1 lien historique.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Click element  css=#content-history .link-overlay
    #Wait until element is visible  css=#content-history #content  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-8-1 historique.png  id=content

Workflow cs
# partie 2.8.3 Courrier sortant
    Enable autologin as  encodeur
    ${RECIPIENT} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25  additional_address_details=41  email=marcleduc@hotmail.com  cell_phone=+324724523453
    Enable autologin as  agent
    ${SENDER} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/agent/agent-grh
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    ${UID} =  Create content  type=dmsoutgoingmail  container=/${PLONE_SITE_ID}/outgoing-mail  title=Réponse candidature  internal_reference_number=S0020
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  sender  ${SENDER}  str
    Set field value  ${UID}  recipients  ['${RECIPIENT}']  references
    Set field value  ${UID}  mail_type  courrier  str
    Sleep  1
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature/create_main_file?filename=Réponse+candidature+ouvrier+communal.odt&title=Réponse+candidature+ouvrier+communal
    Wait until element is visible  css=.DV-pageImage  10
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3 état en création.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    # transitions
    Fire transition  ${UID}  propose_to_service_chief
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3 transition vers chef.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Enable autologin as  chef
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3 état chef.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  propose_to_be_signed
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3 transition vers signature.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3 état à la signature.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  mark_as_sent
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3 état envoyé.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table

Workflow tâche
# partie 2.8.4 Tâches
    Enable autologin as  agent
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    ${OM} =  Create content  type=dmsoutgoingmail  container=/${PLONE_SITE_ID}/outgoing-mail  title=Réponse candidature  internal_reference_number=S0020
    Set field value  ${OM}  treating_groups  ${GRH}  str
    ${UID} =  Create content  type=task  container=${OM}  title=Recontacter en septembre
    Set field value  ${UID}  assigned_group  ${GRH}  str
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature/recontacter-en-septembre
    Wait until element is visible  css=#formfield-form-widgets-ITask-due_date label  10
    Capture and crop page screenshot  doc/utilisation/2-8-4 état en création.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    # transitions
    Fire transition  ${UID}  do_to_assign
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature/recontacter-en-septembre
    Wait until element is visible  css=#plone-contentmenu-workflow .label-state-to_assign
    Capture and crop page screenshot  doc/utilisation/2-8-4 transition vers chef.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Enable autologin as  chef
    Set field value  ${UID}  assigned_user  agent  str
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature/recontacter-en-septembre
    Wait until element is visible  css=#plone-contentmenu-workflow .label-state-to_assign
    Capture and crop page screenshot  doc/utilisation/2-8-4 état à assigner.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  do_to_do
    Enable autologin as  agent
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature/recontacter-en-septembre
    Wait until element is visible  css=#plone-contentmenu-workflow .label-state-to_do
    Capture and crop page screenshot  doc/utilisation/2-8-4 état à faire.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  do_in_progress
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature/recontacter-en-septembre
    Wait until element is visible  css=#plone-contentmenu-workflow .label-state-in_progress
    Capture and crop page screenshot  doc/utilisation/2-8-4 état en cours.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  do_realized
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature/recontacter-en-septembre
    Wait until element is visible  css=#plone-contentmenu-workflow .label-state-realized
    Capture and crop page screenshot  doc/utilisation/2-8-4 état réalisé.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table
    Enable autologin as  chef
    Fire transition  ${UID}  do_closed
    Go to  ${PLONE_URL}/outgoing-mail/reponse-candidature/recontacter-en-septembre
    Wait until element is visible  css=#plone-contentmenu-workflow .label-state-closed
    Capture and crop page screenshot  doc/utilisation/2-8-4 état clôturé.png  id=edit-bar  id=content-history  css=table.actionspanel-no-style-table

Contacts 1
# partie 2.9.1 Recherche de contacts
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/contacts
    Wait until element is visible  css=.contact-entry a[title~=Electrabel]  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-9-1 base.png  id=content
    Select radio button  type  held_position
    Wait until element is visible  css=.contact-entry a[title*="Courant (Electrabel"]  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-9-1 type fonction.png  id=content
    Select radio button  type  person
    Wait until element is visible  css=.contact-entry a[title*="Non encodé"]  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-9-1 type personne.png  id=content
    ### Recherche mot complet
    Input text  css=.section-rechercher-dans-lintitule #texte  Cour
    Click button  css=.section-rechercher-dans-lintitule #texte_button
    Sleep  0.5
    Wait until element is not visible  css=.contact-entry a[title*="Non encodé"]  10
    Wait until element is visible  css=.contact-entry a[title~="Courant"]  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-9-1 texte.png  id=content
    Select radio button  type  organization
    Wait until element is visible  css=#faceted-results #msg-no-results  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-9-1 texte aucun résultat.png  id=content


Contacts 2
# partie 2.9.2 Modification de contacts
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/contacts
    Wait until element is visible  css=.contact-entry a[title~=Electrabel]  10
    Sleep  0.5
    ### icones de gestion
    ${note40}  Add pointy note  css=.contacts-facetednav-action:first-child  Icônes  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-9-2 icone edition.png  id=content  ${note40}
    Remove element  id=${note40}
    Click element  css=.contact-entry:first-child .contacts-facetednav-action:first-child a
    Wait until element is visible  id=formfield-form-widgets-organization_type  10
    Update element style  id=formfield-form-widgets-activity  display  none
    Capture and crop page screenshot  doc/utilisation/2-9-2 edition organisation.png  id=pb_5
    Click button  id=form-buttons-cancel
    Sleep  0.5
    Wait until element is not visible  css=.overlay[style*="display: block"]
    Wait until element is visible  css=.contact-entry a[title~=Electrabel]  10
    Sleep  0.5
    Click element  css=.contact-entry:first-child .contacts-facetednav-action:nth-child(2) a
    Wait until element is visible  css=.overlay[style*="display: block"]  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-9-2 suppression organisation.png  css=.overlay[style*="display: block"]
    Click button  css=.overlay[style*="display: block"] input[name=cancel]
    ### boutons de gestion
    Go to  ${PLONE_URL}/contacts
    Wait until element is visible  css=.contact-entry a[title~=Electrabel]  10
    Sleep  0.5
    Click element  css=.eea-preview-items .contact-entry:first-child .contact-selection input
    Click element  css=.eea-preview-items .contact-entry:nth-child(2) .contact-selection input
    ${note41}  Add pointy note  id=contact-facetednav-action-delete  Suppression sélection  position=top  color=blue
    ${note42}  Add pointy note  id=contact-facetednav-action-merge  Fusion sélection  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-9-2 boutons.png  id=content  ${note41}  ${note42}
    Remove elements  ${note41}  ${note42}
    Click button  id=contact-facetednav-action-merge
    Wait until element is visible  css=form[action*="merge-contacts-apply"]  10
    Capture and crop page screenshot  doc/utilisation/2-9-2 fusion organisation.png  id=content


Configuration
    Enable autologin as  Manager
    Set autologin username  dirg
    Go to  ${PLONE_URL}/@@overview-controlpanel
    Wait until page contains  Configuration de module  10
    Update element style  css=dl.warning  display  None
    ${note50}  Add pointy note  css=.configlets li a[href$="/@@contact-plonegroup-settings"]  Configuration services  position=top  color=blue
    Capture and crop page screenshot  doc/configuration/3-3 Liens config services.png  css=h2:nth-of-type(2)  css=h2:nth-of-type(3)  ${note50}
    Remove element  ${note50}
    ${note51}  Add pointy note  css=.configlets li a[href$="/@@dmsmailcontent-settings"]  Configuration courrier  position=top  color=blue
    Capture and crop page screenshot  doc/configuration/3-3 Liens config courrier.png  css=h2:nth-of-type(2)  css=h2:nth-of-type(3)  ${note51}
    Remove element  ${note51}
    Go to  ${PLONE_URL}/@@dmsmailcontent-settings
    Wait until element is visible  id=formfield-form-widgets-incomingmail_number  10
    Capture and crop page screenshot  doc/configuration/3-3 config courrier.png  id=content
    # Erreur chargement page
    #Go to  ${PLONE_URL}/@@imiodmsmail-settings
    #Wait until element is visible  id=formfield-form-widgets-mail_types  10
    #Capture and crop page screenshot  doc/configuration/3-3 config courrier 2.png  id=content
    #Go to  ${PLONE_URL}/@@contact-plonegroup-settings
    #Wait until element is visible  id=pg-orga-link  10
    #Capture and crop page screenshot  doc/configuration/3-3 config services.png  id=content
    Go to  ${PLONE_URL}/contacts/plonegroup-organization
    Wait until element is visible  id=sub_organizations  10
    Capture and crop page screenshot  doc/configuration/3-3 config propre organisation.png  id=content
# contacts
    Go to  ${PLONE_URL}/contacts/edit
    Wait until element is visible  id=formfield-form-widgets-position_types  10
    Capture and crop page screenshot  doc/configuration/3-3 config contacts.png  id=content

#    Capture viewport screenshot  doc/utilisation/test.png

*** Keywords ***
Suite Setup
    Open test browser
#    Set Window Size  1024  768
    Set Window Size  1280  1200
    Set Window Size  1280  2880
    Set Suite Variable  ${CROP_MARGIN}  5
    Set Selenium Implicit Wait  2
#    Set Selenium Speed  0.3
