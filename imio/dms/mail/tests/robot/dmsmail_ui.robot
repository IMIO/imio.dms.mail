*** Settings ***
Documentation  iA.Docs keywords of the test_*.robot suites, built only on the ui_plone${PLONE_MAJOR}.robot
...            keywords and plone.app.robotframework. Robot Framework 3.0 syntax.
...            Layer: imio.dms.mail.testing.ACCEPTANCE (examples profile: 9 incoming and 9 outgoing mails,
...            users encodeur, agent, chef, dirg..., siteadmin).
Resource  ui_plone${PLONE_MAJOR}.robot


*** Keywords ***
Open the browser
    Open test browser
    Set window size  1280  1600

Log in as
    [Documentation]  Autologin as an existing user, with the given global role
    [Arguments]  ${userid}  ${role}=Member
    Enable autologin as  ${role}
    Set autologin username  ${userid}

Go to the mail
    [Arguments]  ${oid}  ${ptype}=dmsincomingmail
    ${path}=  Get mail path  ptype=${ptype}  oid=${oid}
    Go to  ${PLONE_URL}/${path}

Open the dashboard
    [Documentation]  Dashboard of a top-level folder: incoming-mail, outgoing-mail, contacts...
    [Arguments]  ${folder}
    Go to  ${PLONE_URL}/${folder}
    The dashboard is loaded

Fire the mail transition
    [Documentation]  Server side, as the logged in user
    [Arguments]  ${oid}  ${transition}  ${ptype}=dmsincomingmail
    ${path}=  Get mail path  ptype=${ptype}  oid=${oid}
    ${uid}=  Path to uid  /${PLONE_SITE_ID}/${path}
    Fire transition  ${uid}  ${transition}

The title is
    [Documentation]  A heading of the page contains the title (mails render a hidden title heading
    ...              before the pretty link one, contacts use h1.fn)
    [Arguments]  ${title}
    Wait until page contains element  xpath=//h1[contains(normalize-space(.), "${title}")]

The field contains
    [Documentation]  z3c.form field (display or input mode), by field name
    [Arguments]  ${field}  ${text}
    Wait until element contains  id=formfield-form-widgets-${field}  ${text}

Save the form
    Click button  id=form-buttons-save
