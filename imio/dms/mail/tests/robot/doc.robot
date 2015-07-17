*** Settings ***
Resource  plone/app/robotframework/keywords.robot
Resource  plone/app/robotframework/selenium.robot

Library  Remote  ${PLONE_URL}/RobotRemote
Library  plone.app.robotframework.keywords.Debugging
Library  Selenium2Screenshots

Suite Setup  Suite Setup
Suite Teardown  Close all browsers

*** Variables ***

# ${SELENIUM_RUN_ON_FAILURE} =  Debug

*** Test cases ***

Premiers pas
# partie 2.1 Premiers pas
    Go to  ${PLONE_URL}
    Capture and crop page screenshot  doc/utilisation/2-1 accès à l'application.png  css=.site-plone  id=portal-footer-wrapper
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}
    Capture and crop page screenshot  doc/utilisation/2-1 page d'accueil.png  css=.site-plone  id=portal-footer-wrapper
    Capture and crop page screenshot  doc/utilisation/2-1 fil d'ariane.png  id=breadcrumbs-you-are-here  id=breadcrumbs-home

Encodage depuis le scanner
# partie 2.2.1 Encodage après envoi par le scanner
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Go to  ${PLONE_URL}/incoming-mail
    Capture and crop page screenshot  doc/utilisation/2-2-1 onglet courrier entrant.png  css=.site-plone  id=portal-footer-wrapper
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/@@plone_lock_operations/create_lock
    Go to  ${PLONE_URL}/incoming-mail/collections/searchfor_created
    Capture and crop page screenshot  doc/utilisation/2-2-1 recherche en création.png  css=.site-plone  id=portal-footer-wrapper
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/@@plone_lock_operations/safe_unlock
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail
    Wait until element is visible  css=.DV-pageImage  10

    ### Edit mail
    Capture and crop page screenshot  doc/utilisation/2-2-1 lien modifier courrier.png  id=contentview-edit  id=content-history  css=table.actionspanel-no-style-table
    Go to  ${PLONE_URL}/incoming-mail/dmsincomingmail/edit
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-2-1 édition courrier.png  css=.documentEditable
    Click element  css=.DV-textView span.DV-trigger
    Highlight  css=.DV-textView
    ${note1}  Add pointy note  css=.DV-textView  Onglet texte  position=top  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-1 édition texte océrisé.png  id=portal-columns  ${note1}
    Clear highlight  css=.DV-textView
    Remove element  id=${note1}
    Input text  name=form.widgets.IDublinCore.title  Candidature à un poste d'ouvrier communal
    Input text  name=form.widgets.IDublinCore.description  Lettre de candidature spontanée

    ### Sender field
    Input text  name=form.widgets.sender.widgets.query  le
    Wait until element is visible  css=.ac_results  10
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur recherche le.png  id=fieldset-default
    Click element  id=form-widgets-notes
    Wait until element is not visible  css=.ac_results  10
    Input text  name=form.widgets.sender.widgets.query  leduc

    ### Create contact
    ${note2}  Add pointy note  css=.addnew  Lien nouveau contact  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur recherche leduc.png  id=fieldset-default
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
    Highlight  css=#oform-widgets-organization-autocomplete .addnew
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 1 création lien organisation.png  css=.overlay-contact-addnew  ${note3}
    Remove element  id=${note3}
    Clear highlight  css=#oform-widgets-organization-autocomplete .addnew
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
    Click element  css=.addnew
    Sleep  1
    Input text  name=oform.widgets.person.widgets.query  Leduc
    Wait until element is visible  css=#oform-widgets-person-autocomplete .addnew  10
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 2 création lien personne.png  css=.overlay-contact-addnew
    Click element  css=#oform-widgets-person-autocomplete .addnew
    Wait until element is visible  id=pb_6  10
    Input text  name=form.widgets.firstname  Marc
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
    Wait until element is visible  id=formfield-oform-widgets-position  10
    Update element style  css=.pb-ajax  max-height  800px !important
    Update element style  id=pb_1  top  30px ! important
    Click element  css=#formfield-oform-widgets-plone_0_held_position-end_date label
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 3 création fonction.png  id=pb_1
    Input text  name=oform.widgets.position.widgets.query  Directeur
    Wait until element is visible  css=#oform-widgets-position-autocomplete .addnew  10
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 3 création lien fonction.png  id=pb_1
    Click element  css=#oform-widgets-position-autocomplete .addnew
    Wait until element is visible  id=pb_7  10
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 3 création nouvelle fonction.png  id=pb_7
    Click button  css=#pb_7 #form-buttons-save
    Sleep  1
    Click element  css=#formfield-oform-widgets-plone_0_held_position-end_date label
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 3 création fonction finie.png  id=pb_1
    Click element  css=#pb_1 .close
    #Click button  id=oform-buttons-save

    ### Choose person
    Input text  name=form.widgets.sender.widgets.query  ledu
    Wait until element is visible  css=.ac_results[style*="display: block"]  10
    Click element  css=.ac_results[style*="display: block"] li
    Capture and crop page screenshot  doc/utilisation/2-2-1 expéditeur 0 fini.png  id=fieldset-default

    ### Complete last fields
    Click element  css=.DV-documentView span.DV-trigger
    Select from list by value  id=form-widgets-original_mail_date-day  6
    Select from list by value  id=form-widgets-original_mail_date-month  6
    Select from list by value  id=form-widgets-original_mail_date-year  2012
    Capture and crop page screenshot  doc/utilisation/2-2-1 édition courrier fini.png  css=.documentEditable
    Click button  id=form-buttons-save
    Sleep  2

Encodage manuel
# partie 2.2.2 Encodage manuel du courrier
    Enable autologin as  encodeur
    Go to  ${PLONE_URL}/import_scanned
    Go to  ${PLONE_URL}/incoming-mail

    ### Create incomingmail
    ${note10}  Add pointy note  css=#imiodmsmail-mainportlet table tr a[href*='++add++dmsincomingmail']  Lien d'ajout  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-2 courrier 1 lien ajout.png  id=portal-column-one  ${note10}
    Remove element  id=${note10}
    Click element  css=#imiodmsmail-mainportlet table tr a[href*='++add++dmsincomingmail']
    Wait until element is visible  css=.template-dmsincomingmail #formfield-form-widgets-sender  10
    Sleep  2
    Update element style  id=formfield-form-widgets-IVersionable-changeNote  display  None
    Update element style  id=formfield-form-widgets-ITask-assigned_group  display  None
    Update element style  id=formfield-form-widgets-ITask-enquirer  display  None
    Capture and crop page screenshot  doc/utilisation/2-2-2 courrier 1 création.png  id=content
    Input text  name=form.widgets.IDublinCore.title  Lettre de demande de stage
    Input text  name=form.widgets.sender.widgets.query  Non encod
    Wait until element is visible  css=.ac_results[style*="display: block"]  10
    Click element  css=.ac_results[style*="display: block"] li
    Select from list by value  id=form-widgets-mail_type  courrier
    Select from list by index  id=form-widgets-treating_groups  3
    Click button  id=form-buttons-save
    Sleep  1
    Capture and crop page screenshot  doc/utilisation/2-2-2 courrier 1 création finie.png  id=content  id=viewlet-below-content

    ### Create mainfile
    Update element style  css=#viewlet-above-content-title select[name="Add element"]  padding-right  1em
    ${note11}  Add pointy note  css=#viewlet-above-content-title select[name="Add element"]  Menu ajout d'un élément  position=right  color=blue
    Click element  name=Add element
    Capture and crop page screenshot  doc/utilisation/2-2-2 ged 1 lien ajout.png  id=viewlet-above-content-title  ${note11}
    Remove element  id=${note11}
    Click element  css=#formfield-form-widgets-sender label
    Select from list by index  name=Add element  2
    Wait until element is visible  id=formfield-form-widgets-file  10
    Capture and crop page screenshot  doc/utilisation/2-2-2 ged 1 création.png  id=content
    Click element  id=fieldsetlegend-scan
    Wait until element is visible  id=formfield-form-widgets-IScanFields-scan_id  10
    Capture and crop page screenshot  doc/utilisation/2-2-2 ged 1 création scan.png  id=content
    Click button  id=form-buttons-cancel
    Go to  ${PLONE_URL}/incoming-mail/lettre-de-demande-de-stage/create_main_file?filename=60.PDF
    Go to  ${PLONE_URL}/incoming-mail/lettre-de-demande-de-stage/1/view
    Wait until element is visible  css=.DV-pageImage  10
    ${note12}  Add pointy note  id=breadcrumbs-2  Cliquez ici pour revenir au courrier  position=bottom  color=blue
    Capture and crop page screenshot  doc/utilisation/2-2-2 ged 1 création finie.png  id=portal-column-content  ${note12}
    Remove element  id=${note12}
    Go to  ${PLONE_URL}/incoming-mail/lettre-de-demande-de-stage
    Wait until element is visible  css=.DV-pageImage  10
    Capture and crop page screenshot  doc/utilisation/2-2-2 courrier 2 visualisation.png  id=content

Visualisation
# partie 2.3 Visualisation des éléments
    Go to  ${PLONE_URL}/incoming-mail
    Capture and crop page screenshot  doc/utilisation/2-3 onglet courrier entrant.png  css=.site-plone  id=portal-footer-wrapper
    Go to  ${PLONE_URL}/incoming-mail/courrier3
    Wait until element is visible  css=.DV-pageImage  5
    Capture and crop page screenshot  doc/utilisation/2-3 courrier entrant.png  css=.site-plone  id=portal-footer-wrapper


#    Mouse over  css=#oform-widgets-organization-2-wrapper a.link-tooltip
#    Wait until element is visible  css=div.tooltip #organization  10
    Capture viewport screenshot  doc/utilisation/test.png

*** Keywords ***
Suite Setup
    Open test browser
#    Set Window Size  1024  768
    Set Window Size  1280  800
