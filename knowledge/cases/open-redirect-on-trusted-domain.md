# Open redirect on a trusted domain

## Technique
A legitimate site exposes a redirect endpoint that forwards visitors to any
address passed as a parameter. The attacker builds a link that starts on the
trusted domain and ends on a malicious page, so the first part of the URL
looks safe.

## Warning signs
- A long URL containing another full address inside a query parameter.
- Parameter names such as `url`, `redirect` or `next` holding an external address.

## How to verify
Look at the whole link, not only its beginning. If a second address is
embedded in the parameters, assume the destination is the embedded one.