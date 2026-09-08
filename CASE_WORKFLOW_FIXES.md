# TruthTrace case workflow rules

- Case closing authority: Investigator (for assigned cases) and Administrator (platform-wide). Case Officer remains read-only and cannot close cases.
- Closed cases are hidden from the Administrator case-assignment selector.
- If a closed case reaches the assignment API because of a stale UI/race condition, it is reopened as Active before assignment and the reopening is recorded in the audit trail.
- Once a case is closed, the Close Case action is removed from its workspace header.
- Context Integrity uses human-readable status words: Consistent, Needs Review, Mismatch, and Observed.
- Context summary values use plain English: Strong authenticity signal, Mixed authenticity signal, Weak authenticity signal; and Consistent, Needs review, Inconsistent.
- Muted text contrast was increased so the Palette 5 interface remains readable rather than dull.


## Current closure authority
- Case Officer: may close assigned cases.
- Administrator: may close any case.
- Investigator: cannot close cases.
- Reassigning a closed case as Administrator reopens it and sets status to Active.
