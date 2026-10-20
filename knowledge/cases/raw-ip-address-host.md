# Link pointing to a raw IP address instead of a domain

## Technique
The link uses a numeric address such as `203.0.113.7` in place of a domain
name. Legitimate services almost never ask users to log in through a bare IP.
Attackers use it because a domain registration leaves a trail and an IP on
compromised infrastructure does not.

## Warning signs
- The hostname is four numbers separated by dots.
- The path imitates a login or account page of a known service.

## How to verify
A real service asks for credentials on its own named domain. Treat any
credential form served from a bare IP address as hostile.