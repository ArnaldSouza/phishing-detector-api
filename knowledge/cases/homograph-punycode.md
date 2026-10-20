# Homograph attack using lookalike characters

## Technique
The attacker registers a domain that swaps Latin letters for visually identical
characters from another alphabet, such as Cyrillic. Browsers may render it
exactly like the real brand. Underneath, the hostname is stored in punycode,
which starts with `xn--`.

## Warning signs
- The hostname contains the `xn--` prefix.
- The visible text looks like a known brand, but copying it into a text editor
  shows unusual characters.

## How to verify
Look at the raw hostname, not the rendered one. A legitimate brand domain
almost never needs a punycode label. Type the brand address manually instead
of following the link.