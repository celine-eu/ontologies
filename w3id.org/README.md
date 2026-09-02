# `w3id.org/` — a local Apache for the redirect rules

The CELINE ontology is published at `https://w3id.org/celine-eu`, and what makes
that address work is one `.htaccess` in the [`perma-id/w3id.org`][w3id] repository.
It is submitted by pull request, reviewed by people who do not know this project,
and once merged it is what the whole world hits. Getting it wrong is cheap to do
and expensive to notice: a redirect that serves the HTML page to an RDF client
still returns 200, and nothing complains.

This directory runs those rules against a real Apache before the PR is opened.

## The rules are not in this repository

They live in a clone of the fork, and this harness points at it. There is
deliberately no second copy here — a copy would drift from the one that actually
gets submitted, and the drift would be invisible until review.

```sh
git clone git@github.com:celine-eu/w3id.org.git      # beside the workspace
```

The default location is `../../../../w3id.org` relative to this directory, which
is where it lands if you clone beside the `celine-dev` workspace. Anywhere else,
say so:

```sh
W3ID_CLONE=/path/to/w3id.org task w3id:test
```

## The loop

```sh
task w3id:test              # start Apache, run the matrix, stop Apache
task w3id:test -- --live    # ...and check every target exists on the published site
task w3id:test -- -v        # ...showing each hop
```

Edit `celine-eu/.htaccess` in the clone, run again. **No restart is needed** —
the mount is live and `.htaccess` is read per request.

For a single question:

```sh
task w3id:ask -- /celine-eu 'text/turtle'
task w3id:ask -- /celine-eu/v0.10 'text/html'
```

And when it is green:

```sh
task w3id:diff              # exactly what the PR will contain
```

`task w3id:up` / `w3id:down` / `w3id:logs` are there for poking at it by hand.
Rewrite tracing is on at `trace3`, so `w3id:logs` shows which rule fired.

## What is faithful about it, and what is not

The container mounts the fork's `celine-eu/` as a directory under the document
root with `AllowOverride All` — the same shape the real host uses. That gets the
details that matter:

- **the `DirectorySlash` 301** on `/celine-eu`, which the production host also
  emits and which is a real hop in the chain;
- **`.htaccess` semantics**, not vhost semantics — per-directory, per-request,
  with the leading path segment stripped before `RewriteRule` sees it;
- **mod_rewrite's actual `RewriteCond` evaluation**, including the `[OR]` chains
  the negotiation depends on.

What it does not reproduce: TLS, the production Apache's version and global
config, and any rule outside `celine-eu/`. None of those have ever been the
thing that broke.

## What the matrix covers

`tests/negotiation.py` holds the cases. The four worth knowing about are the
regressions the current rules exist to prevent — every one of them served the
HTML page before 2026-09-02:

| Request | Must get |
|---|---|
| `Accept: text/turtle, application/xhtml+xml;q=0.5, text/html;q=0.3` | `ontology.ttl` |
| `Accept: application/ld+json, text/html;q=0.5` | `ontology.jsonld` |
| `Accept: text/turtle` with a `Mozilla/*` User-Agent | `ontology.ttl` |
| `https://w3id.org/celine-eu/v0.2` in a browser | v0.2's docs, not v0.10's |

Alongside those: a real browser header, the Java default, the OWLAPI header,
rdflib's per-format headers, the versioned IRIs, and the named artifacts.

`--live` additionally asserts that every target returns 200 **with the right
`Content-Type`**. That is not decoration. The rules pointed at
`raw.githubusercontent.com` until 2026-09-02, which serves every serialization as
`text/plain` — so negotiation appeared to work and then misdescribed what it had
served.

## Adding a case

Append to `CASES` in `tests/negotiation.py`: `(label, path, accept, expected)`,
where `path` is relative to the namespace (`""` is the ontology IRI itself) and
`expected` is relative to `https://celine-eu.github.io/ontologies/`.

Add one whenever a review comment or a bug teaches you a request shape nobody
had thought of. That is the point of the file.

## Cutting a version needs nothing here

The rules are generic over `vX.Y`, and the site materialises every version
directory by glob. A new release resolves as soon as the site rebuilds. If it
does not, the site has not rebuilt — check the `celine-docs-update` dispatch
before touching a redirect.

[w3id]: https://github.com/perma-id/w3id.org
