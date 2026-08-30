"""District Vault Mesh — signed cross-district query protocol ("UPI of criminal intelligence").

Architecture (India-Stack analogy, honestly disclosed):

* **District Vaults** are like banks in UPI: each holds its own case data and never
  hands it over. Policing is a State subject (Seventh Schedule) — a central database
  is legally impossible, so queries travel instead of data.
* **Mesh Gateway** is the NPCI-style switch: it routes signed envelopes between
  vaults and keeps a hash-chained ledger of *exchange receipts* — never case data.
* **Envelopes and receipts** are HMAC-SHA256 signed. In production these would be
  NIC-issued certificates; in this offline demo HMAC stands in for the PKI, and the
  protocol shape (sign → route → verify → receipt) is what is being demonstrated.

Everything is dependency-free beyond what the API layer already uses.
"""
