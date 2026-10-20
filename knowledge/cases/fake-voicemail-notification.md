# Voicemail, fax or shared-file notification that leads to a login page

## Technique
The message looks like an automatic notification of a missed call, a voicemail
or a fax, with a button to listen or view it. The button leads to a fake page
asking the recipient to sign in with email credentials, which are then stolen.

## Warning signs
- A notification from a service the recipient does not use.
- A request to sign in just to play a message or open a file.
- A generic sender name and no caller details.

## How to verify
Check the phone or the service's own app for the missed call. Do not sign in
through a link in the message, and look at the address of the page that asks
for the password.