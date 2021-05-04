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

ScrollUp
    Execute javascript  window.scrollTo(0, 0)

ScrollDown
    Execute JavaScript  window.scrollTo(0, document.body.scrollHeight)

Add main note
    [Documentation]  Add a note under the portal top
    [Arguments]  ${text}  ${locator}=id=portal-top
    ${id}  Add note  ${locator}  ${text}  position=bottom  background=#ffc700  color=black  width=400  border=groove
    [return]  ${id}

Add title
    [Documentation]  Add a note under the portal top
    [Arguments]  ${text}
    ${id}  Add note  id=portal-top  ${text}  position=bottom  background=#de007b  color=white  width=400  border=groove
    [return]  ${id}

Add end message
    [Documentation]  Add a note under the portal top
    Add title  Ce tutoriel vidéo est fini ;-) Retrouvez notre documentation complète à l'adresse "https://docs.imio.be".
    sleep  8

Add clic
    [Documentation]  Add a pointer clic on given locator
    [Arguments]  ${locator}
    ${pt1}  Add dot  ${locator}  background=#de007b  size=15
    sleep  1.5
    Remove element  id=${pt1}
    # 4dfc02 green