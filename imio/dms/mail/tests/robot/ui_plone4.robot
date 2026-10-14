*** Settings ***
Documentation  Plone 4.3 keywords. Same keyword names and arguments as ui_plone6.robot.
...            Robot Framework 3.0 syntax (Python 2 environment).
...            Checked on iA.Docs (imio.dms.mail) Plone 4.3: the keywords used by the test_*.robot suites.
...            Not used yet (asset keywords kept for the parity with ui_plone6.robot): Log in with the login form,
...            the content action and personal action keywords, Open the add menu, Cancel the modal,
...            The page is not an error, The page is not found, The edit link is not available.
Resource  plone/app/robotframework/selenium.robot
Resource  plone/app/robotframework/keywords.robot
Library  Remote  ${PLONE_URL}/RobotRemote


*** Variables ***
# jquerytools overlays: every overlay link gets a hidden div.overlay-ajax at page load, the opened one is displayed
${MODAL}  css=div.overlay-ajax[style*="display: block"]
${ERROR_PAGE_TEXT}  there seems to be an error
${NOT_FOUND_TEXT}  This page does not seem to exist


*** Keywords ***
Log in with the login form
    [Documentation]  Real login (creates the user folder), unlike autologin
    [Arguments]  ${username}  ${password}
    Disable autologin
    Go to  ${PLONE_URL}/login_form
    Input text  css=#__ac_name  ${username}
    Input password  css=#__ac_password  ${password}
    Click button  css=input[name="submit"]
    Wait until page contains element  css=#portal-personaltools

Click the content action
    [Documentation]  Item of the Actions menu (object_buttons), by action id
    [Arguments]  ${action_id}
    Click element  css=#plone-contentmenu-actions dt.actionMenuHeader a
    Wait until element is visible  css=#plone-contentmenu-actions-${action_id}
    Click element  css=#plone-contentmenu-actions-${action_id}

The content action is available
    [Arguments]  ${action_id}  ${expected}=${True}
    Click element  css=#plone-contentmenu-actions dt.actionMenuHeader a
    Wait until element is visible  css=#plone-contentmenu-actions dd.actionMenuContent
    Run keyword if  ${expected}
    ...  Page should contain element  css=#plone-contentmenu-actions-${action_id}
    ...  ELSE  Page should not contain element  css=#plone-contentmenu-actions-${action_id}

Open the add menu
    Click element  css=#plone-contentmenu-factories dt.actionMenuHeader a
    Wait until element is visible  css=#plone-contentmenu-factories dd.actionMenuContent

The personal action links to
    [Documentation]  Item of the user menu (user actions), by action id
    [Arguments]  ${action_id}  ${url}
    Element attribute value should be  css=#personaltools-${action_id} a  href  ${url}

The personal action is not available
    [Arguments]  ${action_id}
    Page should not contain element  css=#personaltools-${action_id}

The modal is open
    [Documentation]  Overlay (Plone 4) or modal (Plone 6) showing its loaded content (a form, the quick upload)
    Wait until element is visible  ${MODAL} div.pb-ajax > *

Modal element
    [Documentation]  Locator of the element with this id inside the modal
    ...              (an argument starting with # would be a robot comment)
    [Arguments]  ${id}
    [Return]  ${MODAL} [id="${id}"]

Save the modal
    Click button  ${MODAL} #form-buttons-save

Apply the modal
    [Documentation]  Apply button of the batch action forms
    Click button  ${MODAL} #form-buttons-apply

Cancel the modal
    Click button  ${MODAL} #form-buttons-cancel

The modal is closed
    Wait until element is not visible  ${MODAL}

The status message contains
    [Documentation]  Plone 4 always renders a hidden, empty dl#kssPortalMessage before the real messages
    [Arguments]  ${text}
    Wait until page contains element  xpath=//dl[contains(@class, "portalMessage")][contains(., "${text}")]

The page is not an error
    Page should not contain  ${ERROR_PAGE_TEXT}

The page is not found
    Page should contain  ${NOT_FOUND_TEXT}

The edit link is not available
    Page should not contain element  css=#contentview-edit

# ----------------------------------------------------------------------------
# Faceted dashboards (collective.eeafaceted.*, eea.facetednavigation)
# ----------------------------------------------------------------------------

The dashboard is loaded
    Wait until page contains element  css=#faceted-results .faceted-table-results, #faceted-results .table_faceted_no_results

The dashboard result count is
    [Arguments]  ${count}
    Run keyword if  '${count}' == '0'
    ...  Wait until page contains element  css=#faceted-results .table_faceted_no_results
    ...  ELSE  Wait until keyword succeeds  10s  0.5s  Element text should be  css=#search-results-number  ${count}

The dashboard lists
    [Arguments]  ${title}
    Wait until page contains element  xpath=//table[contains(@class, "faceted-table-results")]//td[contains(., "${title}")]

The dashboard row contains
    [Documentation]  Row whose title cell contains ${title}
    [Arguments]  ${title}  ${text}
    Wait until page contains element
    ...  xpath=//table[contains(@class, "faceted-table-results")]//tr[td[contains(@class, "pretty_link")][contains(., "${title}")]][contains(., "${text}")]

Select the dashboard collection
    [Documentation]  Collection of the left portlet, by title
    [Arguments]  ${title}
    Click element  css=#c1_widget li[title="${title}"] a
    Wait until page contains element  css=#c1_widget li.faceted-tag-selected[title="${title}"]

The dashboard collection count is
    [Documentation]  Counter shown next to a collection of the left portlet
    [Arguments]  ${title}  ${count}
    Wait until keyword succeeds  10s  0.5s  Element text should be  css=#c1_widget li[title="${title}"] .term-count  ${count}

Click the dashboard add link
    [Documentation]  Add icon of the left portlet categories, by a part of its url (e.g. ++add++person)
    [Arguments]  ${url_part}
    Click element  css=#portal-column-one a[href*="${url_part}"]

Search in the dashboard
    [Arguments]  ${text}
    Input text  css=.section-search input[type="text"]  ${text}
    Click button  css=.section-search .searchButton

Select the dashboard rows
    [Documentation]  Only the rows whose title contains one of the given titles are selected
    [Arguments]  @{titles}
    Unselect checkbox  css=#select_unselect_items
    FOR  ${title}  IN  @{titles}
        Select checkbox
        ...  xpath=//tr[td[contains(@class, "pretty_link")][contains(., "${title}")]]//td[contains(@class, "select_item_checkbox")]//input
    END

Click the batch action
    [Documentation]  Button under the dashboard, by batch action id (e.g. treatinggroup); opens a modal
    [Arguments]  ${action_id}
    Click button  css=#${action_id}-batch-action-but
    The modal is open

# ----------------------------------------------------------------------------
# Actions panel (imio.actionspanel)
# ----------------------------------------------------------------------------

Click the panel button
    [Documentation]  Action or transition button of the actions panel above the title, by action or transition id
    [Arguments]  ${id}
    Click element  css=#viewlet-above-content-title .apButtonAction_${id}, #viewlet-above-content-title .apButtonWF_${id}

Add from the panel menu
    [Documentation]  Item of the "Add element" menu of the actions panel, by label
    [Arguments]  ${label}
    Select from list by label  css=#viewlet-above-content-title select[name="Add element"]  ${label}

The workflow state is
    [Arguments]  ${title}
    Wait until element contains  css=.viewlet_workflowstate  ${title}

# ----------------------------------------------------------------------------
# Widgets and viewlets
# ----------------------------------------------------------------------------

Select in the autocomplete widget
    [Documentation]  Contact autocomplete field (collective.contact.widget): type ${search},
    ...              choose the suggestion starting with ${label}
    [Arguments]  ${field}  ${search}  ${label}
    Input text  name=form.widgets.${field}.widgets.query  ${search}
    ${item}=  Set variable
    ...  xpath=//div[contains(@class, "ac_results")][not(contains(@style, "display: none"))]//li[starts-with(normalize-space(.), "${label}")]
    Wait until element is visible  ${item}
    Click element  ${item}

Choose the template in the modal
    [Documentation]  Template of the fancytree shown in the create-from-template modal
    [Arguments]  ${title}
    Click element  xpath=//div[contains(@class, "overlay-ajax")][contains(@style, "display: block")]//span[contains(@class, "fancytree-title")][normalize-space(.)="${title}"]

Upload in the annexes modal
    [Documentation]  Multiple annexes modal (imio.annex quick upload): upload the files with the default category
    [Arguments]  @{paths}
    ${count}=  Get length  ${paths}
    FOR  ${path}  IN  @{paths}
        Choose file  ${MODAL} input[name="file"]  ${path}
    END
    Wait until keyword succeeds  10s  0.5s  Locator should match x times  ${MODAL} .qq-upload-list > li  ${count}
    # the overlay closes at once, the page reloads when every file is uploaded
    Execute javascript  window.robotUploadPending = true;
    Click button  ${MODAL} #uploadify-upload
    Wait for condition  return window.robotUploadPending === undefined  30s

The mail files list
    [Documentation]  Files table of a mail (main files and annexes), by file title
    [Arguments]  ${title}
    Wait until page contains element  xpath=//a[contains(@class, "version-link")][normalize-space(.)="${title}"]

Go to the section of the more tab
    [Documentation]  "● ● ●" portal tab: open its sub menu and follow the link with this title
    [Arguments]  ${title}
    Click element  css=#portaltab-plus a
    Wait until element is visible  css=#subportaltab-plus
    Click link  xpath=//div[@id="subportaltab-plus"]//a[normalize-space(.)="${title}"]
