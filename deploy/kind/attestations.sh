#!/usr/bin/env bash
# What knock attached to a placed image, verified with knock's key before anything is shown:
# the image signature, the provenance (policy, source, source digest — the `digest` of the
# result line) and each SBOM. Any verification failure prints nothing and exits 1.
#
#   deploy/kind/attestations.sh 2.0
#   COSIGN_PUB=other.pub deploy/kind/attestations.sh 2.0   # must fail
set -euo pipefail

TAG="${1:?usage: attestations.sh <tag of shared-test/app>}"
NS=orchestrator
work="$(mktemp -d)"
# Zot through a port of its own (8082 is the zot-ui preview's). Its certificate names the
# service, not localhost: TLS is not checked here, the signatures are.
kubectl -n "$NS" port-forward svc/registry 18082:5000 >/dev/null 2>&1 &
forward=$!
trap 'kill $forward; rm -rf "$work"' EXIT
IMAGE="localhost:18082/shared-test/app:$TAG"
key="${COSIGN_PUB:-$work/cosign.pub}"
[[ -n "${COSIGN_PUB:-}" ]] || kubectl -n "$NS" get secret orchestrator-knock-key \
  -o jsonpath='{.data.cosign\.pub}' | base64 -d > "$key"
until curl -sk -o /dev/null "https://localhost:18082/v2/"; do sleep 1; done

flags=(--key "$key" --new-bundle-format --insecure-ignore-tlog --allow-insecure-registry)
cosign verify "${flags[@]}" "$IMAGE" > "$work/signature.json" 2>/dev/null \
  || { echo "$IMAGE: signature not verified with $key" >&2; exit 1; }
for type in https://knock.dev/predicate/transform/v1 spdxjson cyclonedx; do
  cosign verify-attestation "${flags[@]}" --type "$type" "$IMAGE" 2>/dev/null \
    | head -1 | jq '.payload | @base64d | fromjson' > "$work/${type##*/}.json" \
    || { echo "$IMAGE: $type attestation not verified with $key" >&2; exit 1; }
done

echo "Image     $(jq -r '.[0].critical.image["docker-manifest-digest"]' "$work/signature.json")  signed by knock ✓"
echo
echo "Provenance (https://knock.dev/predicate/transform/v1) ✓"
jq -r '.predicate | "  policy         \(.policy)\n  source         \(.source)\n  source_digest  \(.source_digest)\n  transformed    \(.transformed)"' "$work/v1.json"
echo
echo "SBOM SPDX (https://spdx.dev/Document) ✓"
jq -r '.predicate.packages | "  \(length) packages", (.[] | "  - \(.name) \(.versionInfo // "")")' "$work/spdxjson.json"
echo
echo "SBOM CycloneDX (https://cyclonedx.org/bom) ✓"
jq -r '.predicate.components // [] | "  \(length) components", (.[] | "  - \(.purl // .name)")' "$work/cyclonedx.json"
