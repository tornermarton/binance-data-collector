# HELP
# This will output the help for each task
# thanks to https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## This help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help
.PHONY: help clean build install install-dev uninstall-dev docker-build docker-dist

clean: ## Clean repository
	@rm -rf build/ dist/ .eggs/

build: clean ## Build python package from sources
	@python -m build --wheel --sdist

install: clean ## Install python package from sources
	@pip install .

install-dev: clean ## Install the python package in development mode
	pip install -e .

uninstall-dev: clean ## Uninstall the package installed in development mode
	rm -rf binance_data_collector.egg-info/
	pip uninstall binance_data_collector

docker-build: clean ## Build docker image
	@docker build -t tornermarton/binance-data-collector .

docker-dist: ## Push docker image
	@docker push tornermarton/binance-data-collector
