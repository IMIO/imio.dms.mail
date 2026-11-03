*** Keywords ***

## Actions

Select collection
    [Documentation]  Click element of the collection widget corresponding to given path
    [Arguments]  ${col_path}  ${results}=1  ${widget_name}=c1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${col_path}
    Click element  ${widget_name}${UID}
    Run keyword if  '${results}'=='1'  Wait until element is visible  css=.faceted-table-results  10  ELSE  Wait until element is visible  css=.table_faceted_no_results  10
    Sleep  0.5
#    [Return]  ${UID}

Go to mail
    [Documentation]  Go to a mail page from its id or title
    [Arguments]  ${ptype}=dmsincomingmail  ${oid}=  ${title}=
    ${path} =  Get mail path  ptype=${ptype}  oid=${oid}  title=${title}
    Go to  ${PLONE_URL}/${path}

ScrollUp
    Execute javascript  window.scrollTo(0, 0)

ScrollDown
    Execute JavaScript  window.scrollTo(0, document.body.scrollHeight)

Add main note
    [Documentation]  Add a note under the portal top
    [Arguments]  ${text}  ${locator}=id=portal-top  ${width}=400
    ${id}  Add note  ${locator}  ${text}  position=bottom  background=#ffc700  color=black  width=${width}  border=groove
    [return]  ${id}

Add title
    [Documentation]  Add a note under the portal top
    [Arguments]  ${text}
    ${id}  Add note  id=portal-top  ${text}  position=bottom  background=#de007b  color=white  width=400  border=groove
    [return]  ${id}

Add end message
    [Documentation]  Add a note under the portal top
    ${id}  Add title  Ce tutoriel vidéo est fini ;-) Retrouvez notre documentation complète à l'adresse "https://docs.imio.be".
    sleep  ${N_S}
    sleep  ${N_S}
    Remove element  id=${id}
    sleep  1.5

Add clic
    [Documentation]  Add a pointer clic on given locator
    [Arguments]  ${locator}
    ${pt1}  Add dot  ${locator}  background=#de007b  size=15
    sleep  ${C_S}
    Remove element  id=${pt1}
    # 4dfc02 green

Activate esigning
    [Documentation]  Activate approbation/electronic signature and signing request (singles profile).
    ...  Meant to be called in Suite Setup so every scenario shows the complete configuration.
    Enable autologin as  Manager
    Set autologin username  dirg
    Apply profile step  imio.dms.mail:singles  imiodmsmail-activate-om-signing
    Apply profile step  imio.dms.mail:singles  imiodmsmail-activate-sign-request
    Disable autologin

Show connected user
    [Documentation]  Display a top banner naming the currently connected user (so a video viewer
    ...  always knows who is acting), capture a screenshot, then remove the banner.
    [Arguments]  ${name}  ${shot}
    ${unote}  Add main note  Connecté en tant que : ${name}
    Capture and crop page screenshot  doc/utilisation/${shot}  id=portal-top  ${unote}
    Remove element  id=${unote}

Add outgoing mail for signing
    [Documentation]  Create an outgoing mail (as the current user) filling every required field
    ...  (title, recipients, send_modes via UI ; treating_groups and sender).
    ...  Returns the mail relative path.
    [Arguments]  ${title}
    Go to  ${PLONE_URL}/outgoing-mail
    Wait until element is visible  newOMCreation  10
    Click element  newOMCreation
    Wait until element is visible  css=.template-dmsoutgoingmail #formfield-form-widgets-sender  10
    Sleep  0.5
    Create content  type=person  container=/${PLONE_SITE_ID}/contacts  firstname=Dale  lastname=Cooper  zip_code=4000  city=Belleville  street=Rue Moyenne  number=1991  email=dale.cooper@twinpeaks.com
    Input text  name=form.widgets.IDublinCore.title  ${title}
    Input text  name=form.widgets.recipients.widgets.query  cooper
    Wait until element is visible  css=.ac_results:not([style*="display: none"])  10
    Click element  css=.ac_results:not([style*="display: none"]) li
    Select checkbox  id=form-widgets-send_modes-0
    Click button  id=form-buttons-save
    Wait until element is visible  css=#viewlet-below-content-body table.actionspanel-no-style-table  10
    ${om_path} =  Get mail path  ptype=dmsoutgoingmail  title=${title}
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${om_path}
    ${TG} =  Path to uid  /${PLONE_SITE_ID}/contacts/plonegroup-organization/direction-generale/grh
    Set field value  ${UID}  treating_groups  ${TG}  str
    ${SENDER} =  Path to uid  /${PLONE_SITE_ID}/contacts/personnel-folder/agent/agent-grh
    Set field value  ${UID}  sender  ${SENDER}  str
    [Return]  ${om_path}