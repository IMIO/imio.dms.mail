// bundle plone.bundles/imio-dms-mail-outgoingmail: reload the outgoing mail view when the server says so
document.addEventListener('DOMContentLoaded', function () {

    var evtSource = new EventSource(document.body.dataset.baseUrl + '/server_sent_events');
    evtSource.onmessage = function (e) {
      var selectedFile = document.querySelector('tr.selected .version-link');
      var info = JSON.parse(e.data);
      if (info.refresh || (selectedFile && selectedFile.getAttribute('href').endsWith(info.path))) {
        window.location.reload();
      }
    }
/*    evtSource.onerror = function (e) {
      window.alert("Erreur au rafraichissement automatique");
    }*/
});
