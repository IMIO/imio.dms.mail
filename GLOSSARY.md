# iA.Docs mail

Document management for incoming and outgoing mails, and sign requests, in a local authority.

## Approval and signing

**Signer**:
A held position that signs an outgoing mail or a sign request; the same person with two held positions is two signers.
_Avoid_: signatory, signing person

**Approver**:
A user who approves a document's files on behalf of one signer before that signer signs; on a given document, a user approves for at most one signer.
_Avoid_: validator, reviewer

**Approval**:
An approver's agreement to one file on behalf of one signer; the signers' approvals happen in signer order.
_Avoid_: validation

**Batch approval**:
Approving, from a dashboard, the files of several documents at once; it only covers signers for which it is enabled.
_Avoid_: bulk approval, mass approval

## File editing

**Collabora edit**:
Editing a file's content in the browser, inside iA.Docs; enabled site by site, it then replaces ZopeEdit.
_Avoid_: online editing, WOPI editing

**ZopeEdit**:
Editing a file's content in the office suite installed on the user's computer, launched from iA.Docs; the default.
_Avoid_: external edit, external editor

## Mail intake

**Incoming mail**:
A paper letter received by the authority, scanned and registered in iA.Docs.
_Avoid_: CE, courrier entrant, scanned mail

**Incoming email**:
An email received by the authority and forwarded to iA.Docs.
_Avoid_: IEM, e-mail entrant

**Scan id**:
The 15-digit number identifying a scanned file, printed on the letter as a barcode prefixed with IMIO; its short form, the trailing sequence without leading zeros, is what users type to find it.
_Avoid_: barcode number, CB, numéro de code-barre

**Sender**:
The contact an incoming mail or email comes from: an organization, a person, or a person's held position in an organization.
_Avoid_: expéditeur, author

**Held position**:
A person's role in an organization, such as a club's president; one person can hold several.
_Avoid_: function, occupation

**Encoding**:
Filling in by hand what a scan does not carry (an incoming mail's title, sender, dates and treating services); the encoder's job, never the scanner's.
_Avoid_: indexing, data entry, encodage

## Demo

**Demo site**:
An iA.Docs site set up with sample users, services, contacts and mails to show the product.
_Avoid_: test site, sandbox

**Scanner simulation**:
On a demo site, adding sample incoming mails exactly as the scanner delivers them, with only their file and scan id and nothing encoded, cycling through a fixed set of letters.
_Avoid_: injection, import_scanned
