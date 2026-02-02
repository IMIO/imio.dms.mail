*** Settings ***
Resource  plone/app/robotframework/keywords.robot
Resource  plone/app/robotframework/selenium.robot
Resource  common.robot

Library  OperatingSystem
Library  Remote  ${PLONE_URL}/RobotRemote
Library  Selenium2Screenshots

Suite Setup  Suite Setup
Suite Teardown  Close all browsers

*** Variables ***

#${BROWSER} =  GoogleChrome
${SELENIUM_RUN_ON_FAILURE} =  Debug

*** Test Cases ***

Premiers pas
# partie 2.1 Premiers pas
    [TAGS]  RUN201
    #Log to console  LOG
    Go to  ${PLONE_URL}
    Capture and crop page screenshot  doc/utilisation/2-1-acces-a-lapplication.png  css=.site-plone  id=portal-footer-wrapper
    Enable autologin as  encodeur
    #Log in  encodeur  Dmsmail69!
    Go to  ${PLONE_URL}
    Capture and crop page screenshot  doc/utilisation/2-1-page-daccueil.png  css=.site-plone  id=portal-footer-wrapper
    Capture and crop page screenshot  doc/utilisation/2-1-fil-dariane.png  id=breadcrumbs-you-are-here  id=breadcrumbs-home

CE numerisation
# partie 2.2.1 Numérisation d'un document
    [TAGS]  RUN2021
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned?redirect=
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-2-1-onglet-courrier-entrant.png  css=.site-plone  id=portal-footer-wrapper
    ${im_path} =  Get mail path  oid=dmsincomingmail
    Go to  ${PLONE_URL}/${im_path}/lock-unlock
    Wait until element is visible  css=.DV-pageImage  10
    Select collection  incoming-mail/mail-searches/searchfor_created
    Capture and crop page screenshot  doc/utilisation/2-2-1-recherche-en-creation.png  css=.site-plone  id=portal-footer-wrapper  id=faceted-results
    Go to  ${PLONE_URL}/${im_path}/lock-unlock?unlock=1
    Sleep  1
    Wait until element is visible  css=.DV-pageImage  10

    ### Edit mail
    Capture and crop page screenshot  doc/utilisation/2-2-1-lien-modifier-courrier.png  id=viewlet-above-content-title  id=viewlet-below-content-title
    Go to  ${PLONE_URL}/${im_path}/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-2-1-edition-courrier.png  id=content
    Click element  css=.DV-textView span.DV-trigger
    #Highlight  css=.DV-textView
    ${note1}  Add pointy note  css=.DV-textView  Onglet texte  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-1-edition-texte-ocerise.png  css=h1.documentFirstHeading  ${note1}  id=fieldset-versions
    #Clear highlight  css=.DV-textView
    Remove element  id=${note1}
    Click element  css=.DV-documentView span.DV-trigger
    Input text  name=form.widgets.IDublinCore.title  Candidature à un poste d'ouvrier communal
    Input text  name=form.widgets.IDublinCore.description  Lettre de candidature spontanée

    ### Sender field
    Input text  name=form.widgets.sender.widgets.query  le
    Sleep  0.5
    Wait until element is visible  css=.ac_results  10
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-recherche-le.png  id=formfield-form-widgets-sender  id=formfield-form-widgets-ITask-assigned_user  css=.ac_results[style*="position: absolute"]
    Click element  id=form-widgets-external_reference_no
    Wait until element is not visible  css=.ac_results  10
    Input text  name=form.widgets.sender.widgets.query  leduc

    ### Create contact
    ${note2}  Add pointy note  css=.addnew  Lien nouveau contact  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-recherche-leduc.png  id=formfield-form-widgets-sender  ${note2}  id=formfield-form-widgets-ITask-assigned_user
    Remove element  id=${note2}
    Click element  css=.addnew
    Wait until element is visible  css=.overlay-contact-addnew  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-0-creation.png  css=.overlay-contact-addnew

    ### Create organization
    Input text  name=oform.widgets.organization.widgets.query  IMIO
    Wait until element is visible  css=#oform-widgets-organization-autocomplete .addnew  10
    Update element style  css=#oform-widgets-organization-autocomplete .addnew  padding-right  1em
    ${note3}  Add pointy note  css=#oform-widgets-organization-autocomplete .addnew  Lien nouvelle organisation  position=right  color=blue
    #Highlight  css=#oform-widgets-organization-autocomplete .addnew
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-1-creation-lien-organisation.png  css=.overlay-contact-addnew  ${note3}
    Remove element  id=${note3}
    #Clear highlight  css=#oform-widgets-organization-autocomplete .addnew
    Click element  css=#oform-widgets-organization-autocomplete .addnew
    Wait until element is visible  id=pb_2  10
    Update element style  id=formfield-form-widgets-activity  display  none
    Select from list by value  id=form-widgets-organization_type  sa
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-1-creation-organisation.png  id=pb_2
    Click element  id=fieldsetlegend-contact_details
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-phone  10
    Input text  name=form.widgets.IContactDetails.phone  081586100
    Input text  name=form.widgets.IContactDetails.email  contact@imio.be
    Input text  name=form.widgets.IContactDetails.website  www.imio.be
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-1-creation-organisation-details.png  id=pb_2
    Click element  id=fieldsetlegend-address
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-city  10
    Input text  name=form.widgets.IContactDetails.number  1
    Input text  name=form.widgets.IContactDetails.street  Rue Léon Morel
    Input text  name=form.widgets.IContactDetails.zip_code  5032
    Input text  name=form.widgets.IContactDetails.city  Isnes
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-1-creation-organisation-adresse.png  id=pb_2
    Click button  css=#pb_2 #form-buttons-save
    Sleep  1
    Update element style  css=#oform-widgets-organization-1-wrapper > label  padding-right  1em
    ${note4}  Add pointy note  css=#oform-widgets-organization-1-wrapper > label  Organisation créée et sélectionnée  position=right  color=blue
    #Update element style  css=#oform-widgets-organization-autocomplete .addnew  padding-right  1em
    ${note5}  Add pointy note  css=#oform-widgets-organization-autocomplete .addnew  Lien de création d'un sous-niveau  position=right  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-1-creation-organisation-finie.png  id=pb_1  ${note4}  ${note5}
    Remove elements  ${note4}  ${note5}

    ### Create sub level
    Click element  css=#oform-widgets-organization-autocomplete .addnew
    Wait until element is visible  css=#pb_2 #form-widgets-IBasic-title  10
    Input text  css=#pb_2 #form-widgets-IBasic-title  Département logiciels libres
    Click element  id=fieldsetlegend-contact_details
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-phone  10
    Input text  name=form.widgets.IContactDetails.phone  081586114
    Input text  name=form.widgets.IContactDetails.email  dll@imio.be
    Input text  name=form.widgets.IContactDetails.website  www.imio.be
    Click element  id=fieldsetlegend-address
    Wait until element is visible  id=form-widgets-IContactDetails-use_parent_address-0  10
    Unselect checkbox  id=form-widgets-IContactDetails-use_parent_address-0
    Input text  name=form.widgets.IContactDetails.number  2
    Input text  name=form.widgets.IContactDetails.street  Rue Léon Morel
    Input text  name=form.widgets.IContactDetails.zip_code  5032
    Input text  name=form.widgets.IContactDetails.city  Isnes
    Click button  css=#pb_2 #form-buttons-save
    Sleep  2
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-1-creation-sous-orga-finie.png  id=pb_1

    ### Create person
    Click element  css=#pb_1 .close
    Wait until element is visible  css=.addnew  10
    Sleep  1
    Click element  css=.addnew
    Sleep  2
    Input text  name=oform.widgets.person.widgets.query  Marc Leduc
    Wait until element is visible  css=#oform-widgets-person-autocomplete .addnew  10
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-2-creation-lien-personne.png  css=.overlay-contact-addnew
    Click element  css=#oform-widgets-person-autocomplete .addnew
    Wait until element is visible  id=pb_6  10
    #Input text  name=form.widgets.firstname  Marc
    Click element  id=form-widgets-gender-0
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-2-creation-personne.png  id=pb_6
    Click element  id=fieldsetlegend-contact_details
    Wait until element is visible  id=formfield-form-widgets-IContactDetails-cell_phone  10
    Input text  name=form.widgets.IContactDetails.cell_phone  0472452345
    Input text  name=form.widgets.IContactDetails.email  marcleduc@hotmail.com
    Click element  id=fieldsetlegend-address
    Wait until element is visible  id=form-widgets-IContactDetails-number  10
    Input text  name=form.widgets.IContactDetails.number  25/41
    Input text  name=form.widgets.IContactDetails.street  Rue des Papillons
    Input text  name=form.widgets.IContactDetails.zip_code  4020
    Input text  name=form.widgets.IContactDetails.city  Liège
    Click button  css=#pb_6 #form-buttons-save
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-2-creation-personne-finie.png  id=pb_1

    ### Create function
    Input text  name=oform.widgets.organization.widgets.query  IMIO
    # this results doesn't contain anymore display block .ac_results[style*="display: block"]
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    Click element  css=.ac_results:not([style*="display: none"]) li:nth-child(2)
    Wait until element is visible  css=#formfield-oform-widgets-plone_0_held_position-label input  10
    Update element style  css=.pb-ajax  max-height  800px !important
    Update element style  id=pb_1  top  30px ! important
    Input text  name=oform.widgets.plone_0_held_position.label  Directeur
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-3-creation-fonction-finie.png  id=pb_1
    Click element  css=#pb_1 .close
    #Click button  id=oform-buttons-save
    Sleep  1

    ### Choose person
    Input text  name=form.widgets.sender.widgets.query  ledu
    Wait until element is visible  css=.ac_results[style*="display: block"]  10
    Click element  css=.ac_results[style*="display: block"] li
    Capture and crop page screenshot  doc/utilisation/2-2-1-expediteur-0-fini.png  id=formfield-form-widgets-IDublinCore-description  id=formfield-form-widgets-original_mail_date

    ### Complete last fields
    Select from list by index  id=form-widgets-treating_groups  2
    Sleep  0.5
    scroll down
    Click element  css=#formfield-form-widgets-original_mail_date label
    Select from list by value  id=form-widgets-original_mail_date-day  6
    Select from list by value  id=form-widgets-original_mail_date-month  6
    Select from list by value  id=form-widgets-original_mail_date-year  2012
    Capture and crop page screenshot  doc/utilisation/2-2-1-edition-courrier-fini.png  id=content
    Click button  id=form-buttons-save
    Sleep  2

CE transfert email
# partie 2.2.2 Transfert d'un email
    [TAGS]  RUN2022
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned?number=1&redirect=
    sleep  1
    Go to  ${PLONE_URL}/import_scanned?ptype=dmsincoming_email&number=1&only=email2.pdf&redirect=
    sleep  2
    Go to  ${PLONE_URL}/incoming-mail
    sleep  1
    Wait until element is visible  css=.faceted-table-results  10
    Select collection  incoming-mail/mail-searches/searchfor_created
    sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-2-2-recherche-en-creation-1.png  css=.eea-preview-items
    ${im_path} =  Get mail path  ptype=dmsincoming_email  oid=ou-se-situe-votre-entite-par-rapport-aux-objectifs-de-developpement-durable
    Delete content  /${PLONE_SITE_ID}/${im_path}
    Go to  ${PLONE_URL}/import_scanned?ptype=dmsincoming_email&number=2&only=email1.pdf,email2.pdf&redirect=
    sleep  1
    Enable autologin as  dirg
    ${im_path} =  Get mail path  ptype=dmsincoming_email  oid=reservation-de-la-salle-le-foyer
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${im_path}
    Fire transition  ${UID}  propose_to_agent
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/utilisation/2-2-2-recherche-en-creation-2.png  css=.eea-preview-items
    Enable autologin as  agent
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-2-2-email-a-traiter.png  id=content

CE manuel
# partie 2.2.3 Ajout manuel d'une fiche
    [TAGS]  RUN2023
    Enable autologin as  encodeur
    sleep  1
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.table_faceted_no_results  10

    ### Create incomingmail
    ${note10}  Add pointy note  css=#newIMCreation  Lien d'ajout  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-3-courrier-1-lien-ajout.png  id=portal-column-one  ${note10}
    Remove element  id=${note10}
    Click element  newIMCreation
    Wait until element is visible  css=.template-dmsincomingmail #formfield-form-widgets-sender  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-2-3-courrier-1-creation.png  id=content
    Input text  name=form.widgets.IDublinCore.title  Braderie annuelle septembre
    Input text  name=form.widgets.sender.widgets.query  Non encod
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    Click element  css=.ac_results:not([style*="display: none"]) li
    Select from list by value  id=form-widgets-mail_type  courrier
    Select from list by index  id=form-widgets-treating_groups  10
    Click button  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Capture and crop page screenshot  doc/utilisation/2-2-3-courrier-1-creation-finie.png  id=content  id=viewlet-below-content

    ### Create mainfile
    Update element style  css=#viewlet-above-content-title select[name="Add element"]  padding-right  1em
    ${note11}  Add pointy note  css=#viewlet-above-content-title select[name="Add element"]  Menu ajout d'un élément  position=right  color=blue
    Click element  name=Add element
    # La capture du menu ouvert ne fonctionne pas
    Capture and crop page screenshot  doc/utilisation/2-2-3-ged-1-lien-ajout.png  id=breadcrumbs-you-are-here  ${note11}  css=#parent-fieldname-title span.pretty_link_content
    Remove element  id=${note11}
    Click element  css=#formfield-form-widgets-sender label
    Select from list by label  name=Add element  Fichier ged
    Wait until element is visible  id=formfield-form-widgets-file  10
    Capture and crop page screenshot  doc/utilisation/2-2-3-ged-1-creation.png  id=content
    Click element  id=fieldsetlegend-scan
    Wait until element is visible  id=formfield-form-widgets-IScanFields-scan_id  10
    Capture and crop page screenshot  doc/utilisation/2-2-3-ged-1-creation-scan.png  id=content
    Click button  id=form-buttons-cancel
    ${im_path} =  Get mail path  oid=braderie-annuelle-septembre
    Go to  ${PLONE_URL}/${im_path}/create_main_file?filename=60.PDF
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    ${note12}  Add pointy note  id=breadcrumbs-2  Cliquez ici pour revenir au courrier  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-3-ged-1-creation-finie.png  id=portal-column-content  ${note12}
    Remove element  id=${note12}
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-2-3-courrier-2-visualisation.png  id=content

CE multi-indicatage
    [TAGS]  RUN313
    Enable autologin as  Manager
    Set autologin username  encodeur
    Go to  ${PLONE_URL}/activate_group_encoder
    Wait until element is visible  css=h1.documentFirstHeading
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${im_path} =  Get mail path  oid=dmsincomingmail
    Go to  ${PLONE_URL}/${im_path}/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Scrolldown
    Click element  id=form-widgets-IDmsMailCreatingGroup-creating_group
    Wait until element is visible  id=form-widgets-IDmsMailCreatingGroup-creating_group-1  10
    Capture and crop page screenshot  doc/utilisation/3-1-3-ce-groupe-indicateur.png  id=formfield-form-widgets-internal_reference_no  id=form-buttons-save
    Go to  ${PLONE_URL}/activate_group_encoder?typ=contact
    Wait until element is visible  css=h1.documentFirstHeading
    Go to  ${PLONE_URL}/${im_path}/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/3-1-3-ce-filtre-contact.png  id=formfield-form-widgets-sender

CS en réponse
# partie 2.3.1 Réponse à un courrier entrant
    [TAGS]  RUN2031
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    # set treating_groups value to enable transition
    ${im_path} =  Get mail path  oid=dmsincomingmail
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${im_path}
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  treating_groups  ${GRH}  str
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${DF} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-financiere
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  recipient_groups  ['${DF}']  list
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  external_reference_no  2017/ESB/00123  str
    Go to  ${PLONE_URL}/${im_path}/edit
    Click button  id=form-buttons-save
    Fire transition  ${UID}  propose_to_n_plus_1
    Enable autologin as  dirg
    Fire transition  ${UID}  propose_to_agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    ${note60}  Add pointy note  css=#viewlet-above-content-title .apButtonAction_reply  Bouton de réponse  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-1-lien-repondre.png  id=viewlet-above-content-body  ${note60}
    Remove element  id=${note60}
    Click button  css=#viewlet-above-content-title .apButtonAction_reply
    Wait until element is visible  css=.template-reply #formfield-form-widgets-ITask-due_date  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-1-edition-reponse.png  id=content
    Select checkbox  id=form-widgets-send_modes-0
    Click button  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-1-edition-reponse-finie.png  id=content

    # Create mainfile from model
    ${note51}  Add pointy note  css=#viewlet-above-content-title a.overlay-template-selection  Génération depuis un modèle à sélectionner  position=right  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-3-ged-bouton-selection.png  id=breadcrumbs-you-are-here  ${note51}  css=#parent-fieldname-title span.pretty_link_content
    Remove element  id=${note51}
    Click element  css=#viewlet-above-content-title a.overlay-template-selection
    Wait until element is visible  css=div.pb-ajax
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-3-ged-affichage-liste.png  css=div.pb-ajax
    Click element  css=div.pb-ajax #tree-form li.fancytree-lastsib span.fancytree-expander
    Wait until element is visible  css=div.pb-ajax #tree-form li.fancytree-lastsib li.fancytree-lastsib span.fancytree-title
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-3-ged-affichage-liste-sous-niveau.png  css=div.pb-ajax
    # Click element  css=div.pb-ajax #tree-form li.fancytree-lastsib li.fancytree-lastsib span.fancytree-title
    Click element  css=div.pb-ajax #tree-form span.fancytree-title
    Sleep  0.5
    # Capture and crop page screenshot  doc/utilisation/2-3-1-cs-3-ged-selection-modele.png  css=div.pb-ajax
    # Sleep  5
    ${om_path} =  Get mail path  ptype=dmsoutgoingmail  oid=reponse-candidature-a-un-poste-douvrier-communal
    Go to  ${PLONE_URL}/${om_path}
    Sleep  1
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-3-ged-genere.png  id=content
    ${note52}  Add pointy note  css=#fieldset-versions tr.selected td:nth-child(3)  Édition externe  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-3-ged-edition-externe.png  css=#fieldset-versions table  ${note52}
    Remove element  id=${note52}
    Delete content  /plone/${om_path}/012999900000001

    # Mailing
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${om_path}
    ${REC1} =  Path to uid  /${PLONE_SITE_ID}/contacts/marc-leduc
    ${REC2} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Dexter  lastname=Morgan  zip_code=5000  city=Namur  street=Place du Théâtre  number=5  email=dexter.morgan@mpd.am
    Set field value  ${UID}  recipients  ['${REC1}', '${REC2}']  references
    Go to  ${PLONE_URL}/${om_path}
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-4-creation-finie-multi-dest.png  css=#parent-fieldname-title span.pretty_link_content  id=formfield-form-widgets-ITask-assigned_user
    Click element  css=#viewlet-above-content-title a.overlay-template-selection
    Wait until element is visible  css=div.pb-ajax
    Sleep  0.5
    Click element  css=div.pb-ajax #tree-form li.fancytree-lastsib span.fancytree-expander
    Wait until element is visible  css=div.pb-ajax #tree-form li.fancytree-lastsib li.fancytree-lastsib span.fancytree-title
    Sleep  0.5
    Click element  css=div.pb-ajax #tree-form li.fancytree-lastsib li.fancytree-lastsib span.fancytree-title
    Sleep  5
    Go to  ${PLONE_URL}/${om_path}
    Sleep  1
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-4-ged-genere-non-pub.png  id=content
    ${note55}  Add pointy note  css=a[href*="@@mailing-loop-persistent-document-generation"] > img[src*="mailing.gif"]  Publipostage  position=top  color=blue 
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-4-ged-publipostage.png  css=#fieldset-versions table  ${note55}
    Remove element  id=${note55}
    Click element  css=a[href*="@@mailing-loop-persistent-document-generation"] > img[src*="mailing.gif"]
    Sleep  5
    Go to  ${PLONE_URL}/${om_path}
    Sleep  1
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-4-ged-genere-pub-page-1.png  css=#parent-fieldname-title span.pretty_link_content  id=formfield-form-widgets-internal_reference_no  css=div.viewlet_workflowstate
    # Click element  css=#DV-container .DV-navControls .DV-next
    # Click element  css=#DV-container .DV-navControls .DV-next
    # Capture and crop page screenshot  doc/utilisation/2-3-1-cs-4-ged-genere-pub-page-3.png  id=content
    Delete content  /plone/${om_path}/012999900000001-1
    Delete content  /plone/${om_path}/012999900000001

    ### Add mainfile
    Set field value  ${UID}  recipients  ['${REC1}']  references
    Go to  ${PLONE_URL}/${om_path}
    Sleep  0.5
    #Update element style  css=#viewlet-above-content-title select[name="Add element"]  padding-right  1em
    ${note61}  Add pointy note  css=#viewlet-above-content-title select[name="Add element"]  Menu ajout d'un élément  position=right  color=blue
    Click element  name=Add element
    # La capture du menu ouvert ne fonctionne pas
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-2-ged-lien-ajout.png  css=#parent-fieldname-title span.pretty_link_content  ${note61}
    Remove element  id=${note61}
    Click element  css=#formfield-form-widgets-sender label
    Select from list by label  name=Add element  Fichier ged
    Wait until element is visible  id=formfield-form-widgets-file  10
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-2-ged-ajout.png  id=content
    Click button  id=form-buttons-cancel
    Go to  ${PLONE_URL}/${om_path}/create_main_file?filename=Reponse+candidature+ouvrier+communal.odt&title=Réponse+candidature+ouvrier+communal&mainfile_type=dmsommainfile
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    ${note62}  Add pointy note  id=breadcrumbs-2  Cliquez ici pour revenir au courrier  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-2-ged-ajout-fini.png  id=portal-column-content  ${note62}
    Remove element  id=${note62}
    Go to  ${PLONE_URL}/${om_path}
    Sleep  2
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-1-cs-2-visualisation.png  id=content
    # Delete content  /plone/${om_path}/reponse-candidature-ouvrier-communal

CS nouveau
# partie 2.3.2 Nouveau courrier sortant
# partie 2.3.4 Envoi d'un email sortant
    [TAGS]  RUN2032
    Enable autologin as  agent
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  css=.table_faceted_no_results  10

    ### Create outgoingmail
    ${note1}  Add pointy note  id=newOMCreation  Lien d'ajout  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-2-cs-1-lien-ajout.png  id=portal-column-one  ${note1}
    Remove element  id=${note1}
    Click element  newOMCreation
    Wait until element is visible  css=.template-dmsoutgoingmail #formfield-form-widgets-sender  10
    Sleep  0.5
    Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Dale  lastname=Cooper  zip_code=4000  city=Belleville  street=Rue Moyenne  number=1991  email=dale.cooper@twinpeaks.com
    Capture and crop page screenshot  doc/utilisation/2-3-2-cs-1-creation.png  id=content
    Input text  name=form.widgets.IDublinCore.title  Annonce de la réfection des trottoirs Rue Moyenne
    Input text  name=form.widgets.recipients.widgets.query  cooper
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    Click element  css=.ac_results:not([style*="display: none"]) li
    Select checkbox  id=form-widgets-send_modes-0
    Click button  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    ${om_path} =  Get mail path  ptype=dmsoutgoingmail  oid=annonce-de-la-refection-des-trottoirs-rue-moyenne
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${om_path}
    ${VOIRIES} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-technique/voiries
    Set field value  ${UID}  treating_groups  ${VOIRIES}  str
    ${SENDER} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/agent/agent-voiries
    Set field value  ${UID}  sender  ${SENDER}  str
    Go to  ${PLONE_URL}/${om_path}
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Capture and crop page screenshot  doc/utilisation/2-3-2-cs-1-creation-finie.png  css=table.actionspanel-no-style-table  css=div.viewlet_workflowstate  id=formfield-form-widgets-internal_reference_no
    Go to  ${PLONE_URL}/${om_path}/create_main_file?filename=Refection+trottoir.odt&title=Réfection+trottoir&mainfile_type=dmsommainfile
    Sleep  2
    Wait until element is visible  css=.DV-pageImage  10
    Go to  ${PLONE_URL}/${om_path}
    Sleep  2
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-2-cs-2-visualisation.png  css=table.actionspanel-no-style-table  id=fieldset-versions

    ## Chande send_modes to email
    Set field value  ${UID}  send_modes  ['post', 'email']  list
    Go to  ${PLONE_URL}/${om_path}
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Capture and crop page screenshot  doc/utilisation/2-3-4-cs-mode-email.png  css=table.actionspanel-no-style-table  id=formfield-form-widgets-send_modes
    Go to  ${PLONE_URL}/${om_path}/edit?edit-email=1#fieldsetlegend-email
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-4-cs-edit-email.png  css=h1.documentFirstHeading  id=content-core
    Click element  form-widgets-email_attachments-0
    Click button  id=form-buttons-save
    # Set field value  ${UID}  email_body  <meta charset="UTF-8"><p>Bonjour Monsieur,</p><p>Vous trouverez en pièce jointe un document concernant la réfection des trottoirs dans votre rue.</p><p>Cordialement</p><p>&nbsp;</p><p><span style="font-size:large;font-family:Quicksand,Arial">Fred Agent</span></p><p>&nbsp;</p><div style="float:left;"><div style="font-size:small; float:left;clear:both;width:350px"><span>Agent Voiries</span><br /><span>Direction technique</span><br /><span>Voiries</span><br /><a href="mailto:fred.agent@macommune.be" style="display: inline-block; padding-top: 1em;" target="_blank">fred.agent@macommune.be</a><br /><span>012/34.56.70</span><br /><span style="display: inline-block; padding-top: 0.5em;">Rue de la commune, 1</span><br /><span>0010 Ma ville</span><br /></div><div style="float:left;display: inline-grid;"><a href="" target="_blank"><img alt="" src="/++resource++imio.dms.mail/belleville.png" /></a><br /><span style="font-size:small;text-align: center;">Administration communale de Belleville</span></div><p>&nbsp;</p><div style="font-size: x-small;color:#424242;clear:both"><br />Limite de responsabilité: les informations contenues dans ce courrier électronique (annexes incluses) sont confidentielles et réservées à l'usage exclusif des destinataires repris ci-dessus. Si vous n'êtes pas le destinataire, soyez informé par la présente que vous ne pouvez ni divulguer, ni reproduire, ni faire usage de ces informations pour vous-même ou toute tierce personne. Si vous avez reçu ce courrier électronique par erreur, vous êtes prié d'en avertir immédiatement l'expéditeur et d'effacer le message e-mail de votre ordinateur.</div>  text/html
    # Go to  ${PLONE_URL}/${om_path}
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Capture and crop page screenshot  doc/utilisation/2-3-4-cs-email-visualisation.png  css=table.actionspanel-no-style-table  id=fieldset-versions  id=form-groups-email
    # Click element  css=input.apButtonAction_sendemail # not working on test env

CS depuis le scanner
# partie 2.3.3 Envoi par le scanner
    [TAGS]  RUN2033
    Enable autologin as  scanner
    Go to  ${PLONE_URL}/import_scanned2
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/utilisation/2-3-3-cs-onglet-courrier-sortant.png  css=.site-plone  id=portal-footer-wrapper
    Enable autologin as  encodeur
    ${om_path} =  Get mail path  ptype=dmsoutgoingmail  oid=dmsoutgoingmail
    Go to  ${PLONE_URL}/${om_path}
    Go to  ${PLONE_URL}/${om_path}/lock-unlock
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Select collection  outgoing-mail/mail-searches/searchfor_scanned
    Capture and crop page screenshot  doc/utilisation/2-3-3-cs-recherche-scanne.png  css=.site-plone  id=portal-footer-wrapper  id=faceted-results
    Go to  ${PLONE_URL}/${om_path}/lock-unlock?unlock=1
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10

    ### Edit mail
    Capture and crop page screenshot  doc/utilisation/2-3-3-cs-lien-modifier-courrier.png  id=viewlet-above-content-title  id=viewlet-below-content-title
    Go to  ${PLONE_URL}/${om_path}/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-3-3-cs-edition-courrier.png  id=content
    Click element  css=.DV-textView span.DV-trigger
    ${note1}  Add pointy note  css=.DV-textView  Onglet texte  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-3-3-cs-edition-texte-ocerise.png  id=portal-columns  ${note1}
    Remove element  id=${note1}
    Input text  name=form.widgets.IDublinCore.title  Accusé de réception population
    Select from list by index  id=form-widgets-treating_groups  1
    Click element  s2id_form_widgets_sender
    Input text  s2id_autogen1_search  agent
    Click element  css=#select2-results-1 .select2-results-dept-0
    Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Citoyen  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marccitoyen@hotmail.com
    Input text  name=form.widgets.recipients.widgets.query  Citoyen
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    Click element  css=.ac_results:not([style*="display: none"]) li:first-of-type
    Sleep  0.5
    Click element  css=input#form-widgets-external_reference_no
    Select checkbox  id=form-widgets-send_modes-0
    Click button  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-3-3-cs-creation-finie.png  id=content  id=viewlet-below-content

Menu courrier
# partie 2.4.1 Menu de recherches prédéfinies
    [TAGS]  RUN2041
    Enable autologin as  scanner
    Go to  ${PLONE_URL}/import_scanned?redirect=
    Go to  ${PLONE_URL}/import_scanned2
    Enable autologin as  Manager
    Set autologin username  dirg
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/utilisation/2-4-1-menu-ce.png  css=.portletWidgetCollection
    Capture and crop page screenshot  doc/utilisation/2-4-1-menu-liens-divers.png  css=.portletActionsPortlet
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/utilisation/2-4-1-menu-cs.png  css=.portletWidgetCollection
    Go to  ${PLONE_URL}/tasks
    Wait until element is visible  css=.table_faceted_no_results  10
    Capture and crop page screenshot  doc/utilisation/2-4-1-menu-taches.png  css=.portletWidgetCollection

Tableaux de bord
# partie 2.4.2 Tableaux de bord
    [TAGS]  RUN2042
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned?number=25&redirect=
    ${im_path} =  Get mail path  oid=dmsincomingmail
    Go to  ${PLONE_URL}/${im_path}/lock-unlock
    ${UID0} =  Path to uid  /${PLONE_SITE_ID}/${im_path}
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    ${PERS1} =  Path to uid  /${PLONE_SITE_ID}/contacts/jeancourant
    Set field value  ${UID0}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID0}  treating_groups  ${GRH}  str
    Set field value  ${UID0}  sender  ['${PERS1}']  references
    Set field value  ${UID0}  task_description  <p>Fais ceci</p>  text/html
    Fire transition  ${UID0}  propose_to_n_plus_1
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/utilisation/2-4-2-tableaux-de-bord-general.png  id=content
    Go to  ${PLONE_URL}/${im_path}/lock-unlock?unlock=1
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Click element   css=div.pagination a.next
    Wait until element is visible  css=.faceted-table-results  10
    Unselect checkbox  select_unselect_items
    # treating group
    ${im1_path} =  Get mail path  oid=dmsincomingmail-1
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/${im1_path}
    Select checkbox  css=td.select_item_checkbox input[value='${UID1}']
    Click button  id=treatinggroup-batch-action-but
    Wait until element is visible  css=.pb-ajax #formfield-form-widgets-treating_group  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-4-2-tableaux-de-bord-lot-choix-service.png  css=.pb-ajax
    Click element  css=div.overlay-ajax .close
    # review_state
    Select checkbox  css=td.select_item_checkbox input[value='${UID0}']
    Click button  id=transition-batch-action-but
    Wait until element is visible  css=.pb-ajax #formfield-form-widgets-transition  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-4-2-tableaux-de-bord-lot-transition.png  css=.pb-ajax
    Click element  css=div.overlay-ajax .close
    Unselect checkbox  css=td.select_item_checkbox input[value='${UID0}']
    # recipients
    Click button  id=recipientgroup-batch-action-but
    Wait until element is visible  id=formfield-form-widgets-action_choice  10
    Select from list by value  id=form-widgets-action_choice  replace
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-4-2-tableaux-de-bord-lot-services-en-copie.png  css=.pb-ajax
    Click element  css=div.overlay-ajax .close
    # multiple reply
    # Unselect checkbox  css=td.select_item_checkbox input[value='${UID1}']
    ${PERS2} =  Path to uid  /${PLONE_SITE_ID}/contacts/sergerobinet
    Set field value  ${UID1}  title  Poste d'ouvrier communal  str
    Set field value  ${UID1}  treating_groups  ${GRH}  str
    Set field value  ${UID1}  sender  ['${PERS2}']  references
    ${im2_path} =  Get mail path  oid=dmsincomingmail-2
    ${UID2} =  Path to uid  /${PLONE_SITE_ID}/${im2_path}
    ${PERS3} =  Path to uid  /${PLONE_SITE_ID}/contacts/bernardlermitte
    Set field value  ${UID2}  title  Votre offre pour être ouvrier communal  str
    Set field value  ${UID2}  treating_groups  ${GRH}  str
    Set field value  ${UID2}  sender  ['${PERS3}']  references
    Select checkbox  css=td.select_item_checkbox input[value='${UID2}']
    Select checkbox  css=td.select_item_checkbox input[value='${UID0}']
    Click button  id=reply-batch-action-but
    Wait until element is visible  css=.template-multiple-reply div#formfield-form-widgets-ITask-due_date
    Select from list by index  id=form-widgets-treating_groups  1
    Click element  s2id_form_widgets_sender
    Input text  s2id_autogen1_search  agent
    Click element  css=#select2-results-1 .select2-results-dept-0
    Capture and crop page screenshot  doc/utilisation/2-4-2-tableaux-de-bord-lot-reponse.png  content
    Click button  id=form-buttons-cancel
    Wait until element is visible  css=.faceted-table-results  10
    # widgets
    Wait until element is visible  css=.faceted-sections-buttons-more  10
    Click element  css=.faceted-sections-buttons-more
    Wait until element is visible  id=top---advanced---widgets  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-4-2-tableaux-de-bord-filtres-avances.png  id=top---advanced---widgets  css=div.faceted-sections-buttons
    click element  css=div#s2id_c12.select2-container
    Input text  css=div#s2id_c12.select2-container .select2-input  elec
    Wait until element is visible  css=.select2-drop-active .select2-results  10
    ${span_value}=  Get Text  //div[contains(@class, 'select2-drop-active')]//ul/li[1]/div
    Should Be Equal  ${span_value}  Electrabel
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-4-2-tableaux-de-bord-filtre-expediteur.png  id=top---advanced---widgets  css=#select2-drop .select2-results
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Select collection  incoming-mail/mail-searches/searchfor_created
    Go to  ${PLONE_URL}/${im2_path}
    Capture and crop page screenshot  doc/utilisation/2-4-2-tableaux-de-bord-precedent-suivant.png  id=portal-breadcrumbs  css=#parent-fieldname-title span.pretty_link_content

Recherche générale
# partie 2.4.3 Recherche dans les fichiers scannés
    [TAGS]  RUN2043
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${im1_path} =  Get mail path  oid=dmsincomingmail-1
    ${UID1} =  Path to uid  /${PLONE_SITE_ID}/${im1_path}
    Set field value  ${UID1}  title  Organisation de la braderie annuelle  str
    Capture and crop page screenshot  doc/utilisation/2-4-3-barre-recherche-generale.png  id=portal-globalnav
    Input text  searchGadget  kermes* boudin
    Wait until element is visible  LSResult  10
    Capture and crop page screenshot  doc/utilisation/2-4-3-recherche-livesearch.png  id=portal-searchbox  id=LSResult
    Click button  css=#portal-searchbox .searchButton
    Wait until element is visible  css=.template-search #search-results  10
    Capture and crop page screenshot  doc/utilisation/2-4-3-recherche-avancee.png  css=.template-search #content

Visualisation
# partie 2.5 Visualisation des courriers
    [TAGS]  RUN205
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${im_path} =  Get mail path  oid=dmsincomingmail
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${im_path}
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  description  Candidature spontanée  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  original_mail_date  20170314  date
    #Set field value  ${UID}  reception_date  201703121515  datetime%Y%m%d%H%M
    #Fire transition  ${UID}  propose_to_n_plus_1
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-5-onglet-courrier-entrant.png  css=.site-plone  id=portal-footer-wrapper
    Go to  ${PLONE_URL}/${im_path}
    Sleep  1
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-5-courrier-entrant.png  css=.site-plone  id=portal-footer-wrapper
    # MOUSE MUST BE OUTSIDE BROWSER WINDOW !!!
    Mouse over  css=#form-widgets-sender a.link-tooltip
    Wait until element is visible  css=div.tooltip #person  10
    ## Le pointeur fait disparaître le tooltip
    ##${pointer}  Add pointer  css=#form-widgets-sender a.link-tooltip
    Capture and crop page screenshot  doc/utilisation/2-5-courrier-entrant-personne.png  id=parent-fieldname-title  css=div.tooltip #person
    Click element  css=#labeling-viewlet .pers-edit-1
    Sleep  0.5
    ${note1}  Add pointy note  css=#labeling-viewlet .pers-edit-1  En vert, pour indiquer la lecture  position=right  color=blue
    Capture and crop page screenshot  doc/utilisation/2-5-courrier-entrant-lu.png  parent-fieldname-title  parent-fieldname-description
    Remove element  id=${note1}
    ##Remove element  ${pointer}
    ## La capture du tooltip title ne fonctionne pas!
    #Mouse over  css=a.version-link
    #Sleep  1
    #Capture and crop page screenshot  doc/utilisation/2-5-courrier-entrant-ged.png  id=content

Modification
# partie 2.6 Modification des courriers
    [TAGS]  RUN206
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${im_path} =  Get mail path  oid=dmsincomingmail
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${im_path}
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  description  Candidature spontanée  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  original_mail_date  20170314  date
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    ${note20}  Add pointy note  css=table.actionspanel-no-style-table tr:first-child td  Lien d'édition  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-6-lien-modifier-courrier.png  id=portal-breadcrumbs  id=content-history  css=table.actionspanel-no-style-table  ${note20}
    Remove element  id=${note20}
    Go to  ${PLONE_URL}/${im_path}/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Sleep  0.2
    Capture and crop page screenshot  doc/utilisation/2-6-edition-courrier.png  id=content
    Click button  id=form-buttons-cancel
    Fire transition  ${UID}  propose_to_n_plus_1
    Enable autologin as  chef
    Go to  ${PLONE_URL}/${im_path}/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-6-edition-limitee-courrier.png  id=content
    Click button  id=form-buttons-cancel

Tache
# partie 2.7.1 Ajout d'une tâche
    [TAGS]  RUN207
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${im_path} =  Get mail path  oid=dmsincomingmail
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${im_path}
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  description  Candidature spontanée  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  original_mail_date  20170314  date
    Fire transition  ${UID}  propose_to_manager
    Enable autologin as  dirg
    Go to  ${PLONE_URL}/${im_path}
    Wait until element is visible  css=.DV-pageImage  10
    Sleep  0.5
    Select from list by label  name=Add element  Tâche
    Sleep  0.5
    Wait until element is visible  id=formfield-form-widgets-ITask-assigned_group  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-7-1-tache-ajout-vierge.png  id=content
    Sleep  0.2
    Input text  name=form.widgets.title  Placer le CV dans notre référentiel
    #Input text  css=#formfield-form-widgets-ITask-task_description #content  TEST
    #Select from list by index  name=form.widgets.ITask.assigned_user:list  1
    Click button  id=form-buttons-save
    Wait until element is visible  css=.template-item_view.portaltype-task #formfield-form-widgets-ITask-due_date  10
    Capture and crop page screenshot  doc/utilisation/2-7-1-tache-ajout-complete.png  id=content
    ${TUID} =  Path to uid  /${PLONE_SITE_ID}/${im_path}/placer-le-cv-dans-notre-referentiel
    Fire transition  ${TUID}  do_to_assign
    Go to  ${PLONE_URL}/${im_path}/placer-le-cv-dans-notre-referentiel
    Wait until element is visible  css=div.viewlet_workflowstate span.state-to_assign  10
    Capture and crop page screenshot  doc/utilisation/2-7-1-tache-ajout-to-assign.png  id=content
# partie 2.7.2 Visualisation d'une tâche
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-7-2-tache-dans-courrier.png  id=content
    Go to  ${PLONE_URL}/tasks
    Wait until element is visible  css=.faceted-table-results  10
    Wait until element is visible  css=.th_header_assigned_group  10
    Capture and crop page screenshot  doc/utilisation/2-7-2-tache-dans-tableau.png  id=content

Workflow ce
# partie 2.8.1 Principe et utilisation
    [TAGS]  RUN2081
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${im_path} =  Get mail path  oid=dmsincomingmail
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${im_path}
    ${SENDER} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  original_mail_date  20170314  date
    # db
    Go to  ${PLONE_URL}/incoming-mail
    Wait until element is visible  css=.faceted-table-results  10
    ${note1}  Add pointy note  css=.faceted-table-results tr:nth-child(2) td.td_cell_actions td:first-of-type  Transition  position=top  color=blue
    ${note2}  Add pointy note  transition-batch-action  Transition par lot  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-8-1-transition-tb.png  css=.faceted-table-results > thead  transition-batch-action  recipientgroup-batch-action  ${note2}
    Remove elements  id=${note1}  id=${note2}
    # ce
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2-etat-en-creation.png  css=table.actionspanel-no-style-table  css=div.viewlet_workflowstate
    ${note30}  Add pointy note  css=input.apButtonWF_propose_to_manager  Transition  position=top  color=blue
    ${note31}  Add pointy note  css=input.apButtonWF_propose_to_n_plus_1  Transition  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-8-1-bouton-transition.png  css=div.viewlet_workflowstate  css=table.actionspanel-no-style-table  ${note30}
    Remove elements  id=${note30}  id=${note31}
# partie 2.8.2 ce
    Fire transition  ${UID}  propose_to_manager
    Go to  ${PLONE_URL}/${im_path}
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2-transition-vers-dg.png  css=div.viewlet_workflowstate  id=content-history  id=portal-breadcrumbs
    Enable autologin as  dirg
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2-etat-dg.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  propose_to_n_plus_1
    Enable autologin as  chef
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    ${note32}  Add pointy note  css=#formfield-form-widgets-ITask-assigned_user .formHelp  Avertissement  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-8-2-etat-chef.png  css=table.actionspanel-no-style-table  ${note32}
    Remove element  id=${note32}
    Sleep  0.1
    ${note33}  Add pointy note  css=select.apButtonAction_assign  Assigner un agent  position=right  color=blue
    Capture and crop page screenshot  doc/utilisation/2-8-2-etat-chef-assigne-bouton.png  css=table.actionspanel-no-style-table  ${note33}  css=div.viewlet_workflowstate
    Remove element  id=${note33}
    Go to  ${PLONE_URL}/${im_path}/edit
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    # Capture and crop page screenshot  doc/utilisation/2-8-2-edition-limitee-courrier.png  css=h1.documentFirstHeading  id=formfield-form-widgets-recipient_groups
    Select from list by value  id=form-widgets-ITask-due_date-day  6
    Select from list by value  id=form-widgets-ITask-due_date-month  6
    Select from list by value  id=form-widgets-ITask-due_date-year  2015
    Click button  id=form-buttons-save
    Set field value  ${UID}  assigned_user  agent  field_type normal
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2-etat-chef-assigne.png  css=table.actionspanel-no-style-table  css=div.viewlet_workflowstate  id=formfield-form-widgets-recipient_groups
    Fire transition  ${UID}  propose_to_agent
    Enable autologin as  agent
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2-etat-agent-a-traiter.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  treat
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2-etat-agent-traitement.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  close
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-2-etat-agent-cloture.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    # back & history
    Click button  css=input.apButtonWF_back_to_treatment
    Wait until element is visible  css=form#commentsForm  10
    Input text  name=comment  Réouverture pour apporter une réponse complémentaire.\nSuite à un appel téléphonique.
    # CHANGE locator when overlay bug is resolved
    Capture and crop page screenshot  doc/utilisation/2-8-1-transition-retour.png  id=content  css=form#commentsForm
    Click button  name=form.buttons.save
    Wait until element is visible  css=.highlight-history-link  10
    # CHANGE locator when overlay bug is resolved
    Capture and crop page screenshot  doc/utilisation/2-8-1-transition-fleche-rouge.png  css=#parent-fieldname-title .pretty_link_icons  css=#parent-fieldname-title .pretty_link_content
    Capture and crop page screenshot  doc/utilisation/2-8-1-lien-historique.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    Click element  css=#content-history .link-overlay
    #Wait until element is visible  css=#content-history #content  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-8-1-historique.png  id=content  css=.overlay-history
    Click element  css=#pb_1 .close
    Fire transition  ${UID}  close
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-1-transition-fleche-verte.png  css=#parent-fieldname-title .pretty_link_icons  css=#parent-fieldname-title .pretty_link_content

Workflow cs
# partie 2.8.3 Courrier sortant
    [TAGS]  RUN2083
    Enable autologin as  encodeur
    ${RECIPIENT} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
    Enable autologin as  agent
    ${SENDER} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/agent/agent-grh
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    ${UID} =  Create content  type=dmsoutgoingmail  container=/${PLONE_SITE_ID}/outgoing-mail  title=Réponse candidature  internal_reference_number=S0020
    Set field value  ${UID}  treating_groups  ${GRH}  str
    Set field value  ${UID}  assigned_user  agent  str
    Set field value  ${UID}  sender  ${SENDER}  str
    Set field value  ${UID}  recipients  ['${RECIPIENT}']  references
    # Set field value  ${UID}  mail_type  courrier  str
    Sleep  1
    ${om_path} =  Get mail path  ptype=dmsoutgoingmail  oid=reponse-candidature
    Go to  ${PLONE_URL}/${om_path}/create_main_file?filename=Reponse+candidature+ouvrier+communal.odt&title=Réponse+candidature+ouvrier+communal&mainfile_type=dmsommainfile
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Go to  ${PLONE_URL}/${om_path}
    Sleep  2
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3-etat-en-creation.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    # transitions
    Fire transition  ${UID}  propose_to_n_plus_1
    Go to  ${PLONE_URL}/${om_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3-transition-vers-chef.png  css=div.viewlet_workflowstate  id=content-history  id=content-core
    Enable autologin as  chef
    Go to  ${PLONE_URL}/${om_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3-etat-chef.png  css=div.viewlet_workflowstate  id=content-history  id=portal-breadcrumbs
    Fire transition  ${UID}  propose_to_be_signed
    Go to  ${PLONE_URL}/${om_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3-transition-vers-signature.png  css=div.viewlet_workflowstate  id=content-history  id=portal-breadcrumbs
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/${om_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3-etat-a-la-signature.png  css=div.viewlet_workflowstate  id=content-history  id=portal-breadcrumbs
    Fire transition  ${UID}  mark_as_sent
    Go to  ${PLONE_URL}/${om_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-8-3-etat-envoye.png  css=div.viewlet_workflowstate  id=content-history  id=portal-breadcrumbs

Workflow tâche
# partie 2.8.4 Tâches
    [TAGS]  RUN2084
    Enable autologin as  agent
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    ${OM} =  Create content  type=dmsoutgoingmail  container=/${PLONE_SITE_ID}/outgoing-mail  title=Réponse candidature  internal_reference_number=S0020
    Set field value  ${OM}  treating_groups  ${GRH}  str
    ${UID} =  Create content  type=task  container=${OM}  title=Recontacter en septembre
    Set field value  ${UID}  assigned_group  ${GRH}  str
    ${om_path} =  Get mail path  ptype=dmsoutgoingmail  oid=reponse-candidature
    Go to  ${PLONE_URL}/${om_path}/recontacter-en-septembre
    Wait until element is visible  css=#formfield-form-widgets-ITask-due_date label  10
    Capture and crop page screenshot  doc/utilisation/2-8-4-etat-en-creation.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    # transitions
    Fire transition  ${UID}  do_to_assign
    Go to  ${PLONE_URL}/${om_path}/recontacter-en-septembre
    Wait until element is visible  css=div.viewlet_workflowstate span.state-to_assign
    Capture and crop page screenshot  doc/utilisation/2-8-4-transition-vers-chef.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    Enable autologin as  chef
    Set field value  ${UID}  assigned_user  agent  str
    Go to  ${PLONE_URL}/${om_path}/recontacter-en-septembre
    Wait until element is visible  css=div.viewlet_workflowstate span.state-to_assign
    Capture and crop page screenshot  doc/utilisation/2-8-4-etat-a-assigner.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  do_to_do
    Enable autologin as  agent
    Go to  ${PLONE_URL}/${om_path}/recontacter-en-septembre
    Wait until element is visible  css=div.viewlet_workflowstate span.state-to_do
    Capture and crop page screenshot  doc/utilisation/2-8-4-etat-a-faire.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  do_in_progress
    Go to  ${PLONE_URL}/${om_path}/recontacter-en-septembre
    Wait until element is visible  css=div.viewlet_workflowstate span.state-in_progress
    Capture and crop page screenshot  doc/utilisation/2-8-4-etat-en-cours.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    Fire transition  ${UID}  do_realized
    Go to  ${PLONE_URL}/${om_path}/recontacter-en-septembre
    Wait until element is visible  css=div.viewlet_workflowstate span.state-realized
    Capture and crop page screenshot  doc/utilisation/2-8-4-etat-realise.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table
    Enable autologin as  chef
    Fire transition  ${UID}  do_closed
    Go to  ${PLONE_URL}/${om_path}/recontacter-en-septembre
    Wait until element is visible  css=div.viewlet_workflowstate span.state-closed
    Capture and crop page screenshot  doc/utilisation/2-8-4-etat-cloture.png  css=div.viewlet_workflowstate  id=content-history  css=table.actionspanel-no-style-table

Contacts 1
# partie 2.9.1 Listing des contacts
    [TAGS]  RUN2091
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/contacts
    Wait until element is visible  css=.faceted-table-results  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-9-1-base.png  id=portal-columns
    # MOUSE MUST BE OUTSIDE BROWSER WINDOW !!!
    Mouse over  css=table.faceted-table-results tr:first-child td.pretty_link a.link-tooltip
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-9-1-orga-tooltip.png  css=table.faceted-table-results tr:first-child td.pretty_link a.link-tooltip  css=div.tooltip
    Select collection  contacts/hps-searches/all_hps
    Capture and crop page screenshot  doc/utilisation/2-9-1-type-fonction.png  id=portal-columns
    Select collection  contacts/persons-searches/all_persons
    Capture and crop page screenshot  doc/utilisation/2-9-1-type-personne.png  id=portal-columns
    Select collection  contacts/cls-searches/all_cls
    Capture and crop page screenshot  doc/utilisation/2-9-1-type-liste-contacts.png  id=portal-columns
    Enable autologin as  Contributor  Site Administrator
    Go to  ${PLONE_URL}/contacts
    Wait until element is visible  css=.faceted-table-results  10
    ${note35}  Add pointy note  css=#doc-generation-view ul.pod-template a  Lien d'exportation  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-9-1-export.png  id=content  ${note35}
    Remove element  id=${note35}


Contacts 2
# partie 2.9.2 Gestion de contacts
    [TAGS]  RUN2092
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${im_path} =  Get mail path  oid=dmsincomingmail
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${im_path}
    ${SENDER} =  Path to uid  /${PLONE_SITE_ID}/contacts/electrabel
    ${TG} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale
    Set field value  ${UID}  title  Remplacement du compteur électrique  str
    Set field value  ${UID}  sender  ['${SENDER}']  references
    Set field value  ${UID}  treating_groups  ${TG}  str
    ### icones de gestion
    Go to  ${PLONE_URL}/contacts/electrabel/edit
    Wait until element is visible  id=formfield-form-widgets-organization_type  10
    # Update element style  id=formfield-form-widgets-activity  display  none
    Capture and crop page screenshot  doc/utilisation/2-9-2-edition-organisation.png  content-core
    Click button  id=form-buttons-cancel
    Sleep  0.5
    Go to  ${PLONE_URL}/contacts/electrabel/delete_confirmation
    Wait until element is visible  css=input.destructive  10
    Sleep  0.5
    Capture and crop page screenshot  doc/utilisation/2-9-2-suppression-organisation.png  content
    Click button  css=input[name=cancel]
    ### boutons de gestion
    Go to  ${PLONE_URL}/contacts
    Wait until element is visible  css=.faceted-table-results  10
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/contacts/electrabel
    ${UID2} =  Path to uid  /${PLONE_SITE_ID}/contacts/electrabel/travaux
    Unselect checkbox  select_unselect_items
    Select checkbox  css=td.select_item_checkbox input[value='${UID}']
    Select checkbox  css=td.select_item_checkbox input[value='${UID2}']
    Click button  id=duplicated-batch-action-but
    Wait until element is visible  css=form[action*="merge-contacts-apply"]  10
    Capture and crop page screenshot  doc/utilisation/2-9-2-fusion-organisation.png  id=content

Contacts 3
# partie 2.9.3 Liste de contacts
    [TAGS]  RUN2093
    ### création liste contact
    Enable autologin as  agent
    Go to  ${PLONE_URL}/contacts
    Wait until element is visible  css=.faceted-table-results  10
    Select collection  contacts/cls-searches/all_cls
    ${note36}  Add pointy note  css=#c1_widget ul div.category:nth-child(4) div.title  Icône de création  position=right  color=blue
    Capture and crop page screenshot  doc/utilisation/2-9-3-contact-list-icone.png  css=#portal-column-one div.portletWrapper  ${note36}
    Remove element  id=${note36}
    Go to  ${PLONE_URL}/contacts/contact-lists-folder
    Wait until element is visible  css=table.listing tbody tr:nth-child(2) a.state-private  10
    ${link}=  Get element attribute  css=table.listing tbody tr:nth-child(2) a.state-private  href
    Capture and crop page screenshot  doc/utilisation/2-9-3-contact-list-listing.png  id=content-core
    # Click element  css=table.listing tbody tr:nth-child(2) a.state-private
    Go to  ${PLONE_URL}/contacts/contact-lists-folder/${link}
    Wait until element is visible  css=#content-core p.discreet  10
    ${note37}  Add pointy note  css=#viewlet-above-content-title select[name="Add element"]  Menu ajout d'un élément  position=right  color=blue
    Click element  name=Add element
    Capture and crop page screenshot  doc/utilisation/2-9-3-contact-list-folder.png  id=content  ${note37}
    Remove element  id=${note37}
    ${PERS1} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Marc  lastname=Leduc  zip_code=4020  city=Liège  street=Rue des Papillons  number=25/41  email=marcleduc@hotmail.com  cell_phone=04724523453
    ${PERS2} =  Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Dexter  lastname=Morgan  zip_code=5000  city=Namur  street=Place du Théâtre  number=5  email=dexter.morgan@mpd.am
    Select from list by label  name=Add element  Liste de contacts
    Wait until element is visible  id=formfield-form-widgets-contacts  10
    Input text  name=form.widgets.IBasic.title  Liste des candidats poste DF
    Input text  name=form.widgets.contacts.widgets.query  leduc
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    Click element  css=.ac_results:not([style*="display: none"]) li:first-child
    Input text  name=form.widgets.contacts.widgets.query  morgan
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    Click element  css=.ac_results:not([style*="display: none"]) li:first-child
    Capture and crop page screenshot  doc/utilisation/2-9-3-contact-list-creation.png  id=content
    Click button  form-buttons-save
    Sleep  1
    Select collection  contacts/cls-searches/all_cls
    Capture and crop page screenshot  doc/utilisation/2-9-3-contact-list-dashboard.png  id=content
    ### utilisation liste contact
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned2
    Wait until element is visible  css=.faceted-table-results  10
    ${om_path} =  Get mail path  ptype=dmsoutgoingmail  oid=dmsoutgoingmail
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${om_path}
    ${TG} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/secretariat
    Set field value  ${UID}  treating_groups  ${TG}  str
    Go to  ${PLONE_URL}/${om_path}/edit
    Wait until element is visible  formfield-form-widgets-recipients  20
    Input text  name=form.widgets.IDublinCore.title  Convocation des candidats DF
    Select from list by index  id=form-widgets-treating_groups  1
    Click element  s2id_form_widgets_sender
    Input text  s2id_autogen1_search  agent
    Click element  css=#select2-results-1 .select2-results-dept-0
    Input text  name=form.widgets.recipients.widgets.query  liste candidats
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    Click element  css=.ac_results:not([style*="display: none"]) li:first-child
    Capture and crop page screenshot  doc/utilisation/2-9-3-contact-list-utilisation.png  id=formfield-form-widgets-recipients  id=formfield-form-widgets-IDublinCore-description
    Click element  css=#formfield-form-widgets-mail_date label
    Select checkbox  id=form-widgets-send_modes-0
    Click button  form-buttons-save
    Sleep  1
    Wait until element is visible  css=#form-widgets-recipients li:nth-child(2)  20
    Capture and crop page screenshot  doc/utilisation/2-9-3-contact-list-remplacement.png  id=formfield-form-widgets-recipients

Gestion modèles
# partie 2.10 Gestion des modèles
    [TAGS]  RUN210
	## 2.10.1 Tableau
    Enable autologin as  Manager
    Set autologin username  chef
    Go to  ${PLONE_URL}/templates/om
    # Wait until element is visible  css=#content-core  10
    # Capture and crop page screenshot  doc/utilisation/2-10-1-modeles-docs.png  css=#content
    # Click element  css=.contenttype-folder.state-internally_published.url
    Wait until element is visible  css=.listing.nosort.templates-listing.icons-on  10
    Capture and crop page screenshot  doc/utilisation/2-10-1-tableau-courrier-sortant.png  css=#content
    ## 2.10.2 Modification
    ${note40}  Add pointy note  css=.listing.nosort.templates-listing.icons-on thead tr th:nth-last-child(2)  Actions sur un modèle  position=top  color=blue
    ${note41}  Add pointy note  css=#copy-to-batch-action-but  Actions par lot  position=right  color=blue
    Capture and crop page screenshot  doc/utilisation/2-10-2-actions-sur-un-courrier.png  css=#content
    Remove element  id=${note40}
    Remove element  id=${note41}
    Click element  css=#select_unselect_items
    Click element  css=.listing.nosort.templates-listing.icons-on tbody tr:nth-last-child(2) td:first-child input
    Click element  css=#transition-batch-action-but
    Wait until element is visible  css=.pb-ajax  10
    Capture and crop page screenshot  doc/utilisation/2-10-2-changer-etat-par-lot.png  css=.pb-ajax
    Click element  css=#form-buttons-cancel
    Wait until element is visible  css=#content-core  10
    Click element  css=#copy-to-batch-action-but
    Wait until element is visible  css=.pb-ajax  10
    Capture and crop page screenshot  doc/utilisation/2-10-2-copie-par-lot.png  css=.pb-ajax
    Click element  css=#form-buttons-cancel
    Wait until element is visible  css=#content-core  10
    Go to  ${PLONE_URL}/templates/om/header/edit
    ${note42}  Add pointy note  css=#form-widgets-style_template  Modifier le style utilisé  position=right  color=blue
    Capture and crop page screenshot  doc/utilisation/2-10-2-editer-sous-document.png  css=#content
    Remove element  id=${note42}
    Go to  ${PLONE_URL}/templates/om/main/edit
    # ScrollDown  # doesn't change the fact the capture is outside !
    Wait until element is visible  form-widgets-merge_templates  10
    Update element style  css=#formfield-form-widgets-pod_portal_types  display  None
    ${note43}  Add pointy note  css=#form-widgets-merge_templates tbody tr:first-child td:nth-last-child(2)  Ajouter ou supprimer des sous-modèles  position=left  color=blue
    ${note44}  Add pointy note  css=#form-widgets-merge_templates-4-widgets-template  Choisir le sous-modèle à fusionner  position=bottom  color=blue
	Capture and crop page screenshot  doc/utilisation/2-10-2-fusion-sous-modeles.png  css=#form-widgets-merge_templates  id=${note44}
	Remove element  id=${note43}
	Remove element  id=${note44}
    Go to  ${PLONE_URL}/templates/om
    Capture and crop page screenshot  doc/utilisation/2-10-2-barre-dactions.png  css=.actionspanel-no-style-table.nosort

ia-delib
    [TAGS]  RUN33
    Pass execution  Bypassed due to error
    Enable autologin as  Manager
    Set autologin username  encodeur
    Apply profile step  imio.dms.mail:singles  imiodmsmail-configure-wsclient
    # Unexpected Zope exception: <class 'ZODB.POSException.InvalidObjectReference'> - ('Attempt to store an object from a foreign database connection',  ,  )
    Go to  ${PLONE_URL}/import_scanned
    Wait until element is visible  css=.faceted-table-results  10
    ${im_path} =  Get mail path  oid=dmsincomingmail
    ${UID0} =  Path to uid  /${PLONE_SITE_ID}/${im_path}
    ${GRH} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    ${PERS1} =  Path to uid  /${PLONE_SITE_ID}/contacts/jeancourant
    Set field value  ${UID0}  title  Candidature à un poste d'ouvrier communal  str
    Set field value  ${UID0}  treating_groups  ${GRH}  str
    Set field value  ${UID0}  sender  ['${PERS1}']  references
    Set field value  ${UID0}  task_description  <p>Fais ceci</p>  text/html
    Fire transition  ${UID0}  propose_to_n_plus_1
    Go to  ${PLONE_URL}/${im_path}
    Sleep  0.5
    Wait until element is visible  css=.DV-pageImage  10

Configuration
    [TAGS]  RUN5
    Enable autologin as  Manager
    Set autologin username  dirg
    Go to  ${PLONE_URL}/@@overview-controlpanel
    Wait until page contains  Configuration de module  10
    Update element style  css=dl.warning  display  None
    ${note50}  Add pointy note  css=.configlets li a[href$="/@@contact-plonegroup-settings"]  Configuration services  position=top  color=blue
    Capture and crop page screenshot  doc/configuration/5-4-liens-config-services.png  css=h2:nth-of-type(2)  css=h2:nth-of-type(3)  ${note50}
    Remove element  ${note50}
    # mails
    ${note51}  Add pointy note  css=.configlets li a[href$="/@@dmsmailcontent-settings"]  Configuration courrier  position=top  color=blue
    Capture and crop page screenshot  doc/configuration/5-3-liens-config-courrier.png  css=h2:nth-of-type(2)  css=h2:nth-of-type(3)  ${note51}
    Remove element  ${note51}
    Go to  ${PLONE_URL}/@@dmsmailcontent-settings
    Wait until element is visible  id=formfield-form-widgets-incomingmail_number  10
    Capture and crop page screenshot  doc/configuration/5-3-config-courrier.png  id=content
    Click element  id=fieldsetlegend-outgoingmail
    Wait until element is visible  id=formfield-form-widgets-outgoingmail_number  10
    Capture and crop page screenshot  doc/configuration/5-3-config-courrier-cs.png  id=content
    # Erreur chargement page, voir https://support.imio.be/browse/DMS-434
    #Go to  ${PLONE_URL}/@@imiodmsmail-settings
    #Wait until element is visible  id=formfield-form-widgets-mail_types  10
    # TO DO MANUALLY
    #Capture and crop page screenshot  doc/configuration/5-3-config-courrier-2-ce.png  id=content
    #Capture and crop page screenshot  doc/configuration/5-3-config-courrier-2-cs.png  id=content
    #Capture and crop page screenshot  doc/configuration/5-3-config-courrier-2-contacts.png  id=content
    #Go to  ${PLONE_URL}/@@contact-plonegroup-settings
    #Wait until element is visible  id=pg-orga-link  10
    #Capture and crop page screenshot  doc/configuration/5-4-config-services.png  id=content
    # services
    Go to  ${PLONE_URL}/contacts/plonegroup-organization
    Wait until element is visible  css=table.suborganizations-listing  10
    Capture and crop page screenshot  doc/configuration/5-4-config-propre-organisation.png  id=content
    Go to  ${PLONE_URL}/contacts/personnel-folder
    Wait until element is visible  css=.td_cell_hps  10
    Capture and crop page screenshot  doc/configuration/5-4-config-propre-personnel.png  id=content
    Go to  ${PLONE_URL}/contacts/personnel-folder/chef/edit
    Click element  id=fieldsetlegend-app_parameters
    Wait until element is visible  formfield-form-widgets-IPlonegroupUserLink-userid  10
    Capture and crop page screenshot  doc/configuration/5-4-config-personnel-chef-edit.png  id=content
    Go to  ${PLONE_URL}/contacts/personnel-folder/chef
    Wait until element is visible  css=.subsection-personnel-folder-chef #person #held_positions  10
    Capture and crop page screenshot  doc/configuration/5-4-config-personnel-chef.png  css=table.actionspanel-no-style-table  css=div.viewlet_workflowstate  css=#held_positions div:nth-child(2)
    # users
    Go to  ${PLONE_URL}/@@usergroup-userprefs
    Wait until element is visible  css=table.listing  10
    Capture and crop page screenshot  doc/configuration/5-5-users-listing.png  css=#edit-bar li  css=table.listing  css=input[name='form.button.Modify']
    Go to  ${PLONE_URL}/@@usergroup-groupprefs
    Wait until element is visible  css=table.listing  10
    Capture and crop page screenshot  doc/configuration/5-5-groups-listing.png  css=#edit-bar li  css=table.listing  css=input[name='form.button.Modify']
    Go to  ${PLONE_URL}/@@usergroup-usermembership?userid=agent1
    Wait until element is visible  css=input[name='form.button.Add']  10
    Capture and crop page screenshot  doc/configuration/5-5-user-groups.png  css=#edit-bar li.selected  css=table[summary='Groups']  css=input[name='form.button.Add']
    # contacts
    Go to  ${PLONE_URL}/contacts/edit
    Wait until element is visible  id=formfield-form-widgets-position_types  10
    Capture and crop page screenshot  doc/configuration/5-6-config-contacts.png  id=content
    # doing a screenshot here because folders import doesn't work
    Go to  ${PLONE_URL}/folders
    Wait until element is visible  css=.faceted-table-results  10
    Capture and crop page screenshot  doc/configuration/5-10-import-reussi.png  content
    # classification codes
    # clean demo examples before import
    Go to  ${PLONE_URL}/delete-category?key=-1
    Go to  ${PLONE_URL}/tree
    Wait until element is visible  css=table.actionspanel-no-style-table  10
    Capture and crop page screenshot  doc/configuration/5-9-import-lien.png  id=portal-breadcrumbs  css=table.actionspanel-no-style-table  id=parent-fieldname-title
    Go to  ${PLONE_URL}/tree/@@import
    Wait until element is visible  form-buttons-continue  10
    Capture and crop page screenshot  doc/configuration/5-9-import-part1.png  id=content
    Choose File  id=form-widgets-source-input  ${CURDIR}/tree_parent.csv
    Capture and crop page screenshot  doc/configuration/5-9-import-part1-file.png  id=content
    Click element  form-buttons-continue
    Wait until element is visible  form-buttons-import  10
    Capture and crop page screenshot  doc/configuration/5-9-import-part2.png  id=content
    Click element  form-widgets-decimal_import-0
    Select from list by value  id=form-widgets-column_0  identifier
    Select from list by value  id=form-widgets-column_1  title
    Select from list by value  id=form-widgets-column_2  parent_identifier
    Capture and crop page screenshot  doc/configuration/5-9-import-part2-correspondance.png  id=content
    Click element  form-buttons-import
    Wait until element is visible  css=#table_wrapper table.tree-listing  10
    Capture and crop page screenshot  doc/configuration/5-9-import-reussi.png  css=#portal-column-content > div:nth-child(2)
    # folders
    # clean test folders before import
    Delete content  /${PLONE_SITE_ID}/folders/ordre-public-reglement-general-de-police
    Delete content  /${PLONE_SITE_ID}/folders/reglement-general-de-police-sanctions-administratives-service-de-mediation
    Delete content  /${PLONE_SITE_ID}/folders/controle-des-armes-et-munitions
    Delete content  /${PLONE_SITE_ID}/folders/usage-de-la-voie-publique-stationnement-et-amarrage
    Delete content  /${PLONE_SITE_ID}/folders/usage-de-la-voie-publique-stationnement-et-amarrage-friteries
    Delete content  /${PLONE_SITE_ID}/folders/police-des-edifices-et-lieux-de-reunions-publiques-controle-des-fetes-bals
    Go to  ${PLONE_URL}/folders
    Wait until element is visible  css=.table_faceted_no_results  10
    Sleep  0.5
    Capture and crop page screenshot  doc/configuration/5-10-import-lien.png  portal-column-one  content
    Go to  ${PLONE_URL}/folders/@@import?no_redirect=1
    Wait until element is visible  form-buttons-continue  10
    Capture and crop page screenshot  doc/configuration/5-10-import-part1.png  id=content
    Choose File  id=form-widgets-source-input  ${CURDIR}/folders.csv
    Capture and crop page screenshot  doc/configuration/5-10-import-part1-file.png  id=content
    Click element  form-buttons-continue
    Wait until element is visible  form-buttons-import  10
    Capture and crop page screenshot  doc/configuration/5-10-import-part2.png  id=content
    Select from list by value  id=form-widgets-column_0  folder_categories
    Select from list by value  id=form-widgets-column_1  subfolder_categories
    Select from list by value  id=form-widgets-column_2  folder_title
    Select from list by value  id=form-widgets-column_3  subfolder_title
    Select from list by value  id=form-widgets-column_5  subfolder_archived
    Capture and crop page screenshot  doc/configuration/5-10-import-part2-correspondance.png  id=content
    # validation errors when checking classification_categories
    # Click element  form-buttons-import
    # Wait until element is visible  css=.table-faceted-results  20
    # Capture and crop page screenshot  doc/configuration/5-10-import-reussi.png  content

Annexes dossiers
    [TAGS]  RUN212
    Enable autologin as  Manager
    Set autologin username  dirg
    # Create folder
    Go to  ${PLONE_URL}/folders
    Sleep  2
    Capture and crop page screenshot  doc/utilisation/2-12-folder-view.png  id=faceted-results
    Click Element  css:.pretty_link_icons:first-child img
    Input Text  id=form-widgets-title  Dossier de test
    Input Text  id=form-widgets-classification_categories-widgets-query  con
    Click Element  css:.ac_results li:nth-child(3)
    Select from list by index  id=form-widgets-treating_groups  9  # Service traitant
    Input Text  id=s2id_autogen1  GRH       # Service en copie
    Click Element  css:.select2-result-label
    Input Text  id=form-widgets-classification_informations  Une information capitale
    Select checkbox  id:form-widgets-archived-0
    Click button  id=form-buttons-save
    Sleep  2
    Capture and crop page screenshot  doc/utilisation/2-12-created-folder-view.png  id=portal-column-content
    # Add annexes as files to folder
    Click button  css:.apButton.apButtonAction.apButtonAction_annexes
    Choose File  name:file  ${CURDIR}/annexe.pdf
    Choose File  name:file  ${CURDIR}/Document Kickoff.odt
    Input Text  css:ul li:nth-of-type(1) form input[id="form-widgets-title"]   annexe.pdf
    Input Text  css:ul li:nth-of-type(2) form input[id="form-widgets-title"]   document kickoff.odt
    # Select category of annexes
    Click Element  css:ul li:nth-of-type(2) div[class="select2-container single-select2-widget required choice-field"]
    Input Text  css:.select2-drop.select2-display-none.select2-with-searchbox.select2-drop-active input  delibe
    Click Element  css:ul[id="select2-results-2"] li span[class="plone-annexes_types-annexes-deliberation"]
    Input Text  css:ul li:nth-of-type(2) form textarea[id="form-widgets-description"]  Description de la délibération
    Capture and crop page screenshot  doc/utilisation/2-12-annexe-category.png  id=pb_1
    # Upload annexes
    Click button  id=uploadify-upload
    Go to  ${PLONE_URL}/folders/dossier-de-test/
    Sleep  10
    Capture and crop page screenshot  doc/utilisation/2-12-folder-with-annexes.png  id=portal-column-content
    # Create subfolder
    Go to  ${PLONE_URL}/folders/dossier-de-test/++add++ClassificationSubfolder
    Input Text  id=form-widgets-title  Chemise de test
    Input Text  id=form-widgets-internal_reference_no  F0013-01
    Click button  id=form-buttons-save
    # Add annexes as files to subfolder
    Click button  css:.apButton.apButtonAction.apButtonAction_annexes
    Choose File  name:file  ${CURDIR}/annexe.pdf
    Choose File  name:file  ${CURDIR}/Document Kickoff.odt
    Input Text  css:ul li:nth-of-type(1) form input[id="form-widgets-title"]   annexe.pdf
    Input Text  css:ul li:nth-of-type(2) form input[id="form-widgets-title"]   document kickoff.odt
    # Select category of annexes
    Click Element  css:ul li:nth-of-type(2) div[class="select2-container single-select2-widget required choice-field"]
    Input Text  css:.select2-drop.select2-display-none.select2-with-searchbox.select2-drop-active input  delibe
    Click Element  css:ul[id="select2-results-2"] li span[class="plone-annexes_types-annexes-deliberation"]
    Click button  id=uploadify-upload
    # Link a CE in the new subfolder
    Go to  ${PLONE_URL}/incoming-mail
    Click Element  id=newIMCreation
    Input Text  id=form-widgets-IDublinCore-title  Création d'une fiche courrier entrant
    # Sender Field
    Input text  name=form.widgets.sender.widgets.query  Elec
    Click element  css=.ac_results:not([style*="display: none"]) li:nth-child(2)
    # Treating group
    Click Element  id=form-widgets-treating_groups
    Select from list by index  id=form-widgets-treating_groups  3
    # Others fields
    Select from list by value  id=form-widgets-mail_type  courrier
    Click element  css=#formfield-form-widgets-original_mail_date label
    Select from list by value  id=form-widgets-original_mail_date-day  6
    Select from list by value  id=form-widgets-original_mail_date-month  6
    Select from list by value  id=form-widgets-original_mail_date-year  2012
    # Classification code
    Input Text  name=form.widgets.IClassificationFolder.classification_categories.widgets.query  Con
    scroll down
    Scrolldown
    Click element  css=.ac_results:not([style*="display: none"]) li:nth-child(3)
    # Folder
    Input Text  name=form.widgets.IClassificationFolder.classification_folders.widgets.query  Test
    Click element  css=.ac_results:not([style*="display: none"]) li:nth-child(2)
    Click button  id=form-buttons-save
    # Check the result and screenshots
    Go to  ${PLONE_URL}/tree
    Capture and crop page screenshot  doc/utilisation/2-12-tree.png  id=content
    Go to  ${PLONE_URL}/folders/
    Click Element  css:.pretty_link_content.state-active

Debug
    [TAGS]  DBG
    Pass execution  Only for debug purpose
    Enable autologin as  Manager
    Set autologin username  dirg
    Go to  ${PLONE_URL}/@@imiodmsmail-settings#fieldsetlegend-contact
    debug

*** Keywords ***
Suite Setup
    ${FF_PROFILE_DIR} =  Get Environment Variable  ROBOT_FF_PROFILE_DIR  None
    Set global variable  ${FF_PROFILE_DIR}
    Open test browser
    # Set Window Size  1080  1920
    # Set Window Size  1260  2880
    # Set Window Size  1260  2240
    Set Window Size  1200  1920
    Set Suite Variable  ${CROP_MARGIN}  5
    Set Selenium Implicit Wait  2
    Set Selenium Speed  0.2
    Enable autologin as  Manager
    Set autologin username  dirg
    Go to  ${PLONE_URL}/robot_init
    Disable autologin
    # Pause
