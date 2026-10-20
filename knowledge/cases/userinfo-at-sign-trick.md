# Misleading text before an at sign in the URL

## Technique
URLs allow a "user information" part before an `@`, so in
`https://brand.com@attacker.example/` the real destination is the text after
the `@`. The attacker places a trusted name first so the link reads as if it
leads to that brand.

## Warning signs
- An `@` character inside a link.
- A familiar brand name directly before the `@`.

## How to verify
The hostname is whatever follows the last `@` and ends at the next `/`.
Legitimate links to a service almost never contain an `@`.