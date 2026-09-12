# Vendored fonts

## Astronomicon.ttf

Astrological symbol face, version 1.1, from https://astronomicon.co/en/astronomicon-fonts/
Released under the SIL Open Font License — see `OFL-License.txt`.

Vendored rather than downloaded at build time. The workflow used to fetch a font over the
network and that fetch had been 404ing silently for the life of the project: `curl` wrote the
9-byte "Not Found" body to a `.ttf`, `fc-cache` ignored it, and every chart was drawn in
whatever the fallback happened to be. A file in the repo cannot fail that way.

**This font maps symbols onto ASCII letters, not Unicode.** `A`–`L` are Aries through Pisces,
`Q`–`Z` are Sun through Pluto, `M` is retrograde. See `ASTRO_SIGN_GLYPHS` / `ASTRO_BODY_GLYPHS`
in `renderers/base.py`. Never set it on anything but symbols: point it at a date and the digits
survive but every letter turns into a planet.
