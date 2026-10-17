# Contrat commun à regis, knock et uske : la CI n'appelle que ces cibles.
.PHONY: ci-tools lint test security image smoke settings

CI_IMAGE ?= uske:ci
ARGO ?= $(shell command -v argo || echo .bin/argo)

ci-tools: ## Installe argo dans .bin/ (version et empreinte épinglées)
	mkdir -p .bin
	curl -sfL -o .bin/argo.gz https://github.com/argoproj/argo-workflows/releases/download/v4.1.4/argo-linux-amd64.gz
	echo "2c8ef41d53593f2ee64d85fb69b631c89a0fc2c57e6ce011422caa525a97ec58  .bin/argo.gz" | sha256sum -c -
	gunzip -f .bin/argo.gz && chmod +x .bin/argo

lint: ## ruff, puis les manifestes rendus par kustomize, validés par argo et relus par leur test
	uv run ruff check .
	uv run ruff format --check .
	@d="$$(mktemp -d)" && trap 'rm -rf "$$d"' EXIT && \
	kubectl kustomize deploy/kind > "$$d/uske.yaml" && $(ARGO) lint --offline "$$d/uske.yaml"
	uv run python -m pytest --no-cov -q tests/test_manifests.py

test: ## Tests et couverture de branches (90 %)
	uv run python -m pytest

security: ## pip-audit, bloquant à partir de HIGH (commande identique dans les trois dépôts)
	@d="$$(mktemp -d)" && trap 'rm -rf "$$d"' EXIT && \
	uv export -q --locked --all-extras --no-dev --no-emit-project --no-hashes -o "$$d/req.txt" && \
	{ uvx pip-audit==2.10.1 -r "$$d/req.txt" --no-deps --disable-pip --progress-spinner off --format=json --output "$$d/audit.json" || true; } && \
	test -s "$$d/audit.json" && \
	python3 .github/pip-audit-gate.py "$$d/audit.json" --min-severity HIGH

image: ## Construit l'image et la teste
	docker build -t $(CI_IMAGE) .
	$(MAKE) smoke CI_IMAGE=$(CI_IMAGE)

smoke: ## Vérifie qu'une image démarre : make smoke CI_IMAGE=<ref>
	docker run --rm $(CI_IMAGE) --help

settings: ## Applique .github/settings.json au dépôt
	.github/apply-settings.sh
