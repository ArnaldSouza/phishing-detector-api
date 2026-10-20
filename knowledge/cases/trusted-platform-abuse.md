# Phishing hosted on a trusted platform

## Technique
The attacker publishes the phishing page on a legitimate service, such as a
form builder, a document-sharing site, or a free site builder. The hostname
belongs to a reputable company, so reputation checks and hostname-based
analysis pass.

## Warning signs
- A form or shared document asking for passwords or payment data.
- A message that routes you to a generic platform page rather than the
  organization's own site.

## How to verify
Hostname analysis cannot detect this class of attack, because the domain
really is legitimate. Judge the content and context: no organization should
collect credentials through a generic form. Report the page to the platform.