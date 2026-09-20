#!/usr/bin/env bash
# Local environment for the orchestrator: kind + Argo Workflows + a plain registry for Harbor,
# the published regis and knock. Then one screening, started by hand.
#
#   deploy/kind/up.sh
#   deploy/kind/up.sh dt      # then Dependency-Track, on that cluster
#   deploy/kind/up.sh down
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HERE="$ROOT/deploy/kind"
CLUSTER=orchestrator
NS=orchestrator
KNOCK="ghcr.io/trivoallan/knock@sha256:2381703b01eb791ebf2d4f91dc2dc403f759b52bd1db0913904f6d0d3e77087d"  # 0.12.0
REGISTRY="registry.$NS.svc.cluster.local:5000"

if [[ "${1:-}" == "down" ]]; then
  kind delete cluster --name "$CLUSTER"
  exit 0
fi

# Dependency-Track, on a cluster `up.sh` has built: it watches, after admission, the SBOM knock
# signed, which dt-sync feeds it. Throwaway: no volume, and a fixed admin password, reachable only
# through a port-forward. Vulnerability data: OSV for Go only, which the 2.0 candidate needs.
if [[ "${1:-}" == "dt" ]]; then
  DT=dependency-track
  DT_PASSWORD=orchestrator
  kubectl config use-context "kind-$CLUSTER" >/dev/null
  kubectl create namespace "$DT" --dry-run=client -o yaml | kubectl apply -f -
  # Created once: a new KEK would make the secrets already encrypted in PostgreSQL unreadable.
  kubectl -n "$DT" get secret dt-db >/dev/null 2>&1 || kubectl -n "$DT" create secret generic dt-db \
    --from-literal=username=dtrack --from-literal=password="$(openssl rand -hex 16)"
  kubectl -n "$DT" get secret dt-kek >/dev/null 2>&1 || kubectl -n "$DT" create secret generic dt-kek \
    --from-literal=kek="$(openssl rand -base64 32)"
  kubectl -n "$DT" apply -f "$HERE/dependency-track.yaml"
  kubectl -n "$DT" rollout status deploy/postgresql --timeout=180s
  helm repo add dependency-track https://dependencytrack.github.io/helm-charts >/dev/null 2>&1 || true
  helm upgrade --install dependency-track dependency-track/dependency-track --version 2.4.0 \
    --namespace "$DT" --wait --timeout 15m \
    --set database.existingSecret.name=dt-db \
    --set secretManagement.database.kek.existingSecret.name=dt-kek \
    --set fileStorage.local.size=1Gi \
    --set frontend.apiBaseUrl=http://localhost:8083  # the UI is a static app: the browser calls the API

  # Configuration through the API, on a port of its own (8083 is the dt-api preview's).
  kubectl -n "$DT" port-forward svc/dependency-track-api-server 18083:8080 >/dev/null 2>&1 &
  forward=$!
  trap 'kill $forward' EXIT
  api=http://localhost:18083/api
  until curl -fsS "$api/version" >/dev/null 2>&1; do sleep 2; done
  # Only accepted while admin/admin is still the forced first password.
  curl -sS -o /dev/null -X POST "$api/v1/user/forceChangePassword" -d username=admin -d password=admin \
    -d newPassword="$DT_PASSWORD" -d confirmPassword="$DT_PASSWORD"
  auth="Authorization: Bearer $(curl -fsS -X POST "$api/v1/user/login" -d username=admin -d password="$DT_PASSWORD")"
  sources="$api/v2/extension-points/vuln-data-source/extensions"
  # NVD, on by default, mirrors the whole CVE catalogue for hours.
  curl -fsS -X PUT -H "$auth" -H 'Content-Type: application/json' "$sources/nvd/config" \
    -d '{"config": {"enabled": false, "cveFeedsUrl": "https://nvd.nist.gov/feeds"}}'
  curl -fsS -X PUT -H "$auth" -H 'Content-Type: application/json' "$sources/osv/config" \
    -d '{"config": {"enabled": true, "dataUrl": "https://storage.googleapis.com/osv-vulnerabilities",
         "ecosystems": ["Go"], "aliasSyncEnabled": false, "incrementalMirroringEnabled": true}}'
  latest() { curl -sS -H "$auth" "$api/v2/vuln-data-sources/osv/mirror-runs/latest" | jq -r '.status // "NONE"'; }
  if [[ "$(latest)" != COMPLETED ]]; then
    [[ "$(latest)" == RUNNING ]] || curl -fsS -X POST -H "$auth" "$api/v2/vuln-data-sources/osv/mirror-runs" >/dev/null
    until [[ "$(latest)" == COMPLETED ]]; do
      [[ "$(latest)" != FAILED ]] || { echo "OSV mirror failed" >&2; exit 1; }
      sleep 5
    done
  fi
  # dt-sync's access: a team with bounded permissions (change dt-sync, decision 9), its API key in
  # the orchestrator's namespace. Created once: a new key per run would pile up in the team.
  team="$(curl -fsS -H "$auth" "$api/v1/team" | jq -r '.[] | select(.name == "dt-sync") | .uuid')"
  [[ -n "$team" ]] || team="$(curl -fsS -X PUT -H "$auth" -H 'Content-Type: application/json' \
    "$api/v1/team" -d '{"name": "dt-sync"}' | jq -r .uuid)"
  for permission in BOM_UPLOAD PROJECT_CREATION_UPLOAD VIEW_PORTFOLIO \
      PORTFOLIO_MANAGEMENT_READ PORTFOLIO_MANAGEMENT_CREATE PORTFOLIO_MANAGEMENT_UPDATE; do
    curl -sS -o /dev/null -X POST -H "$auth" "$api/v1/permission/$permission/team/$team"  # 304 if held
  done
  if ! kubectl -n "$NS" get secret orchestrator-dt >/dev/null 2>&1; then
    key="$(curl -fsS -X PUT -H "$auth" "$api/v1/team/$team/key" | jq -r .key)"
    kubectl -n "$NS" create secret generic orchestrator-dt --from-literal=DT_API_KEY="$key" \
      --from-literal=DT_URL="http://dependency-track-api-server.$DT.svc.cluster.local:8080"
  fi
  echo "Dependency-Track ready (admin / $DT_PASSWORD), OSV Go mirrored. Feed it the placed images:"
  echo "  kubectl -n $NS create -f $HERE/sync.yaml && kubectl -n $NS get wf -w"
  echo "API: kubectl -n $DT port-forward svc/dependency-track-api-server 8083:8080"
  echo "UI:  kubectl -n $DT port-forward svc/dependency-track-frontend 8084:8080  → http://localhost:8084"
  exit 0
fi

# 1. Cluster, with this repository mounted on the node for the checkout step.
if ! kind get clusters | grep -qx "$CLUSTER"; then
  kind create cluster --name "$CLUSTER" --config - <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    extraMounts:
      - {hostPath: "$ROOT", containerPath: /repository, readOnly: true}
EOF
fi
kubectl config use-context "kind-$CLUSTER" >/dev/null
kubectl create namespace "$NS" --dry-run=client -o yaml | kubectl apply -f -

# 2. Argo Workflows, watching this namespace only.
helm repo add argo https://argoproj.github.io/argo-helm >/dev/null 2>&1 || true
helm upgrade --install argo-workflows argo/argo-workflows --namespace "$NS" --wait \
  --set singleNamespace=true \
  --set "controller.workflowNamespaces={$NS}" \
  --set "server.authModes={server}"

# 3. Images, loaded into the node.
docker build -q --provenance=false -f "$ROOT/Dockerfile" -t orchestrator:dev "$ROOT"
# A candidate with no package at all, built here: one file on scratch.
printf 'FROM scratch\nCOPY README.md /README.md\n' | docker build -q --provenance=false -t candidate-empty:dev -f - "$ROOT"
# A candidate with packages that passes regis: a Go binary on scratch (for Dependency-Track).
docker build -q --provenance=false -t candidate-go:dev "$HERE/candidate-go"
docker pull -q "$KNOCK" >/dev/null
# ponytail: through an archive; `kind load docker-image` fails on Docker Desktop's containerd
# store for multi-platform images. Zot, regis and knock (published) are pulled by the node.
archive="$(mktemp)"
for image in orchestrator:dev candidate-empty:dev candidate-go:dev; do
  docker save -o "$archive" "$image"
  kind load image-archive --name "$CLUSTER" "$archive"
done
rm -f "$archive"

# 4. TLS and secrets. A self-signed CA and Zot's certificate; a trust bundle (public CAs, which
# grype needs for its database, plus ours) handed to every tool through SSL_CERT_FILE; knock's
# test signing key; the registry roster.
REGIS="ghcr.io/trivoallan/regis@sha256:95fc4bbdb87e77726c3d79f4977ed3c8d80c4141017797d031b1ba0f03783f5a"  # 0.38.1-full
if ! kubectl -n "$NS" get secret registry-tls >/dev/null 2>&1; then
  tls="$(mktemp -d)"
  # Full extensions: Python's ssl verifies strictly (key usage on the CA, key identifiers).
  openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=orchestrator kind CA" \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -keyout "$tls/ca.key" -out "$tls/ca.crt" 2>/dev/null
  openssl req -newkey rsa:2048 -nodes -subj "/CN=registry" -keyout "$tls/tls.key" -out "$tls/tls.csr" 2>/dev/null
  printf '%s\n' "subjectAltName=DNS:registry,DNS:registry.$NS.svc,DNS:${REGISTRY%:*}" \
    "keyUsage=critical,digitalSignature,keyEncipherment" "extendedKeyUsage=serverAuth" \
    "authorityKeyIdentifier=keyid" "subjectKeyIdentifier=hash" > "$tls/san"
  openssl x509 -req -in "$tls/tls.csr" -CA "$tls/ca.crt" -CAkey "$tls/ca.key" -CAcreateserial \
    -days 30 -extfile "$tls/san" -out "$tls/tls.crt" 2>/dev/null
  docker run --rm --entrypoint cat "$REGIS" /etc/ssl/certs/ca-certificates.crt > "$tls/bundle.pem"
  cat "$tls/ca.crt" >> "$tls/bundle.pem"
  kubectl -n "$NS" create secret tls registry-tls --cert="$tls/tls.crt" --key="$tls/tls.key"
  kubectl -n "$NS" create secret generic registry-ca --from-file=bundle.pem="$tls/bundle.pem"
  docker run --rm -e COSIGN_PASSWORD= -v "$tls:/keys" -w /keys --entrypoint cosign "$KNOCK" \
    generate-key-pair >/dev/null
  kubectl -n "$NS" create secret generic orchestrator-knock-key \
    --from-file=cosign.key="$tls/cosign.key" --from-file=cosign.pub="$tls/cosign.pub"
  rm -rf "$tls"
fi
kubectl -n "$NS" create secret generic orchestrator-knock \
  --from-literal=KNOCK_REGISTRIES="{\"local\": {\"host\": \"$REGISTRY\"}}" \
  --from-literal=KNOCK_ATTEST_SIGNER=key --from-literal=KNOCK_ATTEST_KEY_REF=/keys/cosign.key \
  --from-literal=COSIGN_PASSWORD= --from-literal=SSL_CERT_FILE=/etc/registry-ca/bundle.pem \
  --from-literal=KNOCK_SBOM_FORMATS='["spdx-json","cyclonedx-json"]' \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create secret generic orchestrator-harbor \
  --from-literal=HARBOR_HOST="$REGISTRY" --from-literal=SSL_CERT_FILE=/etc/registry-ca/bundle.pem \
  --dry-run=client -o yaml | kubectl apply -f -

# 5. The orchestrator and the registry (Zot, for the node's architecture).
arch="$(docker exec "$CLUSTER-control-plane" uname -m | sed 's/aarch64/arm64/;s/x86_64/amd64/')"
kubectl kustomize "$HERE" | sed "s/zot-linux-arm64/zot-linux-$arch/" | kubectl apply -n "$NS" -f -
kubectl -n "$NS" rollout status deploy/registry --timeout=120s

# knock's public key becomes Zot's only trusted cosign key: a green badge then means "signed at
# admission by knock", nothing else (design, decision 13).
kubectl -n "$NS" delete pod trust-key --ignore-not-found >/dev/null
kubectl -n "$NS" run trust-key --rm -i --restart=Never --image=orchestrator:dev --overrides='{"spec":{
  "containers":[{"name":"t","image":"orchestrator:dev","imagePullPolicy":"Never",
    "env":[{"name":"SSL_CERT_FILE","value":"/ca/bundle.pem"}],
    "command":["python","-c","import urllib.request as u; r=u.Request(\"https://registry:5000/v2/_zot/ext/cosign\", data=open(\"/key/cosign.pub\",\"rb\").read(), method=\"POST\"); print(\"trusted key uploaded:\", u.urlopen(r).status)"],
    "volumeMounts":[{"name":"ca","mountPath":"/ca"},{"name":"key","mountPath":"/key"}]}],
  "volumes":[{"name":"ca","secret":{"secretName":"registry-ca"}},{"name":"key","secret":{"secretName":"orchestrator-knock-key"}}]}}'

# 6. Three producer tags in the registry, three real images: 1.1 is the
#    orchestrator image (Alpine, busybox under GPL-2.0: what the licence rule sees, DEBT-13).
#    1.0 is a scratch image holding one file (no package). 2.0 is a Go binary on scratch whose
#    dependency has known advisories: placed (CVE rules only warn in redistribution), then
#    watched by Dependency-Track (`up.sh dt`).
# Pushed from the node, which already holds the image and reaches the service IP (the Docker
# Desktop daemon lives in a VM and cannot see a host port-forward).
NODE="$CLUSTER-control-plane"
ip="$(kubectl -n "$NS" get svc registry -o jsonpath='{.spec.clusterIP}')"
platform="linux/$(docker exec "$NODE" uname -m | sed 's/aarch64/arm64/;s/x86_64/amd64/')"  # only this one is on the node
for pair in 1.0=docker.io/library/candidate-empty:dev 1.1=docker.io/library/orchestrator:dev 2.0=docker.io/library/candidate-go:dev; do
  tag="${pair%%=*}"
  docker exec "$NODE" ctr -n k8s.io images tag --force "${pair#*=}" "$ip:5000/producer/app:$tag" >/dev/null
  docker exec "$NODE" ctr -n k8s.io images push --local --skip-verify --platform "$platform" "$ip:5000/producer/app:$tag" >/dev/null
done
# No candidate list: each screening, knock's plan names what it would copy (D-30).

# 7. Known products for the demonstration policies (change politiques-de-demonstration): copied
#    once into Zot under mirror/, whole index by digest, so what regis judges here is byte for
#    byte what the 2026-09-19 spike judged. After this, no network is needed.
CRANE="gcr.io/go-containerregistry/crane/debug@sha256:94f61956845714bea3b788445454ae4827f49a90dcd9dac28255c4cccb6220ad"  # v0.20.3
MIRRORS="
docker.io/library/redis@sha256:520775a41a63e77e06c73e35d2fd9cc15921a609516818796b4ecbb813078bc7 mirror/redis:7.4-alpine
registry.k8s.io/coredns/coredns@sha256:40384aa1f5ea6bfdc77997d243aec73da05f27aed0c5e9d65bfa98933c519d97 mirror/coredns:v1.12.0
gcr.io/distroless/static-debian12@sha256:afa5c872c891853ca7fcf1f12c3edb23f7eeef36189728842dd51042ff57f7ab mirror/distroless-static:nonroot
docker.io/library/nginx@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10 mirror/nginx:1.27-alpine
ghcr.io/sigstore/cosign/cosign@sha256:6bbe0d281d955c79f85b325f0f7e651c1bcab5a4fa4ad4903d74955178a3b2eb mirror/cosign:v3.1.1
registry.k8s.io/pause@sha256:ee6521f290b2168b6e0935a181d4cff9be1ac3f505666ef0e3c98fae8199917a mirror/pause:3.10
docker.io/library/hello-world@sha256:5e23090353324d887c48ad5e5c56d294eab81588df9605b07d1afe895f9cc8f8 mirror/hello-world:latest"
script='while read -r src dst; do
  [ -n "$src" ] || continue
  if crane digest "$REGISTRY/$dst" >/dev/null 2>&1; then echo "present $dst"; else crane copy "$src" "$REGISTRY/$dst" && echo "copied $dst"; fi
done'
kubectl -n "$NS" delete pod mirror --ignore-not-found >/dev/null
kubectl -n "$NS" run mirror --rm -i --restart=Never --image="$CRANE" --overrides="$(jq -n \
  --arg image "$CRANE" --arg script "$script" --arg mirrors "$MIRRORS" --arg registry "$REGISTRY" '{spec: {
  containers: [{name: "m", image: $image, command: ["sh", "-c", ($script + " <<EOF\n" + $mirrors + "\nEOF")],
    env: [{name: "REGISTRY", value: $registry}, {name: "SSL_CERT_FILE", value: "/ca/bundle.pem"}],
    volumeMounts: [{name: "ca", mountPath: "/ca"}]}],
  volumes: [{name: "ca", secret: {secretName: "registry-ca"}}]}}')"

echo "Ready. Start a screening:"
echo "  kubectl -n $NS create -f $HERE/screening.yaml && kubectl -n $NS get wf -w"
echo "Argo UI:     kubectl -n $NS port-forward svc/argo-workflows-server 2746:2746  → https://localhost:2746"
echo "Registry UI: kubectl -n $NS port-forward svc/registry 8082:5000               → https://localhost:8082"
echo "What knock attached to a placed image, verified: $HERE/attestations.sh 2.0"
echo "Dependency-Track: $0 dt, then a dt-sync pass: kubectl -n $NS create -f $HERE/sync.yaml"
