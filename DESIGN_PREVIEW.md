# Approved design and production status

The ivory, navy and gold theme now covers public pages, the admin login and all organizer pages. The owner-supplied RV logo appears in site branding and browser icons. The QRIS/Midtrans footer badge is removed. Shared inline SVG icons, trophy artwork and gold/silver/bronze top-three podiums remain in place.

Production is live at https://rajavotedigital.my.id. See [deployment and verification](deploy/ivory-gold-20261010.md) for the release directory, backup, test evidence and limits.

The design was integrated into the newer, hardened Tencent source before deployment. Existing backend behavior, payment-disabled controls, safe HTML rendering, authenticated exports and native checkout dialogs are preserved. Production serves prebuilt Tailwind rather than the development CDN.

The isolated local fixture preview is available at http://127.0.0.1:8766 while its temporary runner remains active. It uses a separate SQLite database under `/tmp/rvd-public-preview`; no preview data or credentials were deployed. Temporary runners and screenshots are not deployment tooling.
