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
