# The decisions only: regis and knock keep their own images, policies and playbooks come
# from a repository checkout at run time. Build from the repository root:
#   docker build -t uske .
# cosign verifies the SBOM attestation knock signed before dt-sync sends it (change dt-sync).
FROM ghcr.io/sigstore/cosign/cosign:v3.1.1@sha256:6bbe0d281d955c79f85b325f0f7e651c1bcab5a4fa4ad4903d74955178a3b2eb AS cosign

FROM python:3.13-alpine
COPY --from=cosign /ko-app/cosign /usr/local/bin/cosign
RUN pip install --no-cache-dir pyyaml==6.0.2
WORKDIR /app
COPY uske/ uske/
USER 65532
ENTRYPOINT ["python", "-m", "uske"]
