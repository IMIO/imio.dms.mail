/srv/archgenxml/agx26/bin/archgenxml --cfg agx.conf imiodmsmail.zargo
#manage generated.pot
#cp temp/i18n/generated.pot ../locales/agx.pot

#copying workflows
#cp temp/profiles/default/workflows.xml ../profiles/default
cp -r temp/profiles/default/workflows ../profiles/default

#change the workflow name
sed -i 's/title=\"incomingmail_workflow\"/title=\"Incoming mail workflow\"/g' ../profiles/default/workflows/incomingmail_workflow/definition.xml

