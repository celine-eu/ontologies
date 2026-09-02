#!/usr/bin/env python3
"""Exercise the celine-eu .htaccess against a real Apache.

Run indirectly: `task w3id:test`. The harness in this directory starts httpd with
the fork's `celine-eu/` mounted as a namespace directory, so what is under test is
mod_rewrite's actual behaviour, not a reimplementation of it.

Two things are checked, and they fail for different reasons:

  * the *rule* — where a given (path, Accept) is redirected to. Needs the local
    Apache and nothing else.
  * the *target* — whether that URL exists on the published site. Needs the
    network, and is skipped unless --live is passed.

A rule can be right while its target 404s: that is what happens when the
.htaccess is landed before the site that serves it has rebuilt.
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request

SITE = "https://celine-eu.github.io/ontologies/"

BROWSER = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,"
    "image/avif,image/webp,*/*;q=0.8"
)
JAVA = "text/html, image/gif, image/jpeg, *; q=.2, */*; q=.2"
OWLAPI = (
    "application/rdf+xml, application/xml;q=0.5, text/xml;q=0.5, text/turtle;q=0.5"
)
RDFLIB_TTL = "text/turtle, application/x-turtle, */*;q=0.1"

# (label, path under the namespace, Accept, expected target relative to SITE)
# An optional 5th element overrides the User-Agent.
CASES = [
    # ── the ontology IRI ───────────────────────────────────────────────────
    ("browser",                  "",  BROWSER,             "index-en.html"),
    ("explicit html",            "",  "text/html",         "index-en.html"),
    ("curl default",             "",  "*/*",               "index-en.html"),
    ("no Accept at all",         "",  None,                "index-en.html"),
    ("java default",             "",  JAVA,                "index-en.html"),
    ("turtle",                   "",  "text/turtle",       "ontology.ttl"),
    ("rdflib turtle",            "",  RDFLIB_TTL,          "ontology.ttl"),
    ("n3",                       "",  "text/n3, */*;q=0.1", "ontology.ttl"),
    ("rdf/xml",                  "",  "application/rdf+xml", "ontology.owl"),
    ("json-ld",                  "",  "application/ld+json", "ontology.jsonld"),
    ("n-triples",                "",  "application/n-triples", "ontology.nt"),
    ("owlapi",                   "",  OWLAPI,              "ontology.owl"),
    # These four are the regressions this file exists to prevent. Every one of
    # them returned the HTML page before 2026-09-02.
    ("turtle listed before html", "", "text/turtle, application/xhtml+xml;q=0.5, text/html;q=0.3", "ontology.ttl"),
    ("json-ld before html",      "",  "application/ld+json, text/html;q=0.5", "ontology.jsonld"),
    ("rdf/xml before html",      "",  "application/rdf+xml, text/html;q=0.9", "ontology.owl"),
    # The old rules put the User-Agent test inside the [OR] chain, so a browser-ish
    # UA overrode an explicit Accept. A library that spoofs Mozilla must still get RDF.
    ("turtle with Mozilla UA",   "",  "text/turtle",       "ontology.ttl", "Mozilla/5.0"),
    ("browser UA and header",    "",  BROWSER,             "index-en.html", "Mozilla/5.0"),
    # A stated preference is honoured: whichever type is listed first wins.
    ("turtle preferred",         "",  "text/turtle, application/rdf+xml;q=0.5", "ontology.ttl"),
    ("rdf/xml preferred",        "",  "application/rdf+xml, text/turtle;q=0.5", "ontology.owl"),

    # ── versioned IRIs resolve to their own version ────────────────────────
    ("v0.10 browser",            "v0.10",  BROWSER,       "v0.10/index-en.html"),
    ("v0.10 turtle",             "v0.10",  "text/turtle", "v0.10/ontology.ttl"),
    ("v0.10 trailing slash",     "v0.10/", "text/turtle", "v0.10/ontology.ttl"),
    ("v0.9 json-ld",             "v0.9",   "application/ld+json", "v0.9/ontology.jsonld"),
    ("v0.2 browser",             "v0.2",   BROWSER,       "v0.2/index-en.html"),

    # ── artifacts addressed by name, no negotiation ────────────────────────
    ("jsonld context",  "v0.10/celine.jsonld",      BROWSER,       "v0.10/celine.jsonld"),
    ("json schema",     "v0.10/celine.schema.json", "*/*",         "v0.10/celine.schema.json"),
    ("shacl shapes",    "v0.10/celine.shacl.ttl",   "text/turtle", "v0.10/celine.shacl.ttl"),
    ("v0.5 context",    "v0.5/celine.jsonld",       "*/*",         "v0.5/celine.jsonld"),
    ("serialization",   "v0.10/ontology.nt",        "*/*",         "v0.10/ontology.nt"),
]

# Content-Type the published site must return, checked only under --live.
EXPECTED_TYPE = {
    ".ttl": "text/turtle",
    ".owl": "application/rdf+xml",
    ".jsonld": "application/ld+json",
    ".nt": "application/n-triples",
    ".html": "text/html",
    ".json": "application/json",
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def request(url: str, accept: str | None, method: str = "GET",
            user_agent: str = "celine-w3id-test/1"):
    req = urllib.request.Request(url, method=method)
    req.remove_header("User-agent")
    req.add_header("User-Agent", user_agent)
    if accept is None:
        # urllib always sends one; an empty value is the closest to "no preference"
        req.add_header("Accept", "")
    else:
        req.add_header("Accept", accept)
    try:
        resp = OPENER.open(req, timeout=15)
        return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers)


def resolve(base: str, path: str, accept: str | None,
            user_agent: str = "celine-w3id-test/1") -> tuple[str, list[str]]:
    """Follow the local chain to the first off-host redirect. Returns (target, hops)."""
    url = f"{base}/celine-eu" + (f"/{path}" if path else "")
    hops = []
    for _ in range(5):
        status, headers = request(url, accept, user_agent=user_agent)
        location = headers.get("Location")
        hops.append(f"{status} {url}")
        if not location:
            return url, hops
        if not location.startswith(base):
            return location, hops
        url = location
    return url, hops


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://w3id.localhost:8730")
    ap.add_argument("--live", action="store_true",
                    help="also check each target exists on the published site")
    ap.add_argument("-v", "--verbose", action="store_true", help="show the hop chain")
    args = ap.parse_args()

    print(f"Apache under test: {args.base}\n")
    failures = 0
    for case in CASES:
        label, path, accept, expected = case[:4]
        user_agent = case[4] if len(case) > 4 else "celine-w3id-test/1"
        want = SITE + expected
        try:
            got, hops = resolve(args.base, path, accept, user_agent)
        except Exception as exc:  # noqa: BLE001 — report, do not abort the table
            print(f"  ERROR {label:26} {exc}")
            failures += 1
            continue
        ok = got == want
        failures += not ok
        shown = got[len(SITE):] if got.startswith(SITE) else got
        shown = shown or got  # the site root strips to nothing; show it whole
        print(f"  {'ok  ' if ok else 'FAIL'} {label:26} -> {shown}")
        if not ok:
            print(f"       expected {expected}")
        if args.verbose:
            for hop in hops:
                print(f"         {hop}")

    print(f"\nrules: {len(CASES) - failures}/{len(CASES)} as intended")

    if args.live:
        print("\nchecking the published targets exist:")
        live_failures = 0
        for target in sorted({SITE + c[3] for c in CASES}):
            status, headers = request(target, "*/*", method="HEAD")
            ctype = headers.get("Content-Type", "").split(";")[0].strip()
            suffix = "." + target.rsplit(".", 1)[-1]
            want_type = EXPECTED_TYPE.get(suffix)
            ok = status == 200 and (want_type is None or ctype == want_type)
            live_failures += not ok
            print(f"  {'ok  ' if ok else 'FAIL'} {status} {ctype:24} {target[len(SITE):]}")
        print(f"\ntargets: {len(({SITE + c[3] for c in CASES})) - live_failures}"
              f"/{len({SITE + c[3] for c in CASES})} reachable with the right type")
        failures += live_failures

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
