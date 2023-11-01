define Comment
	- Run `make help` to see all the available options.
	- Run `make test` to run all tests.
	- Run `make publish` to publish to PyPI.
endef


.PHONY: help
help:  ## Show this help message.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'


.PHONY: test
test:  ## Run the tests.
	poetry install
	docker start ide_db_server || docker run --name ide_db_server -e MYSQL_DATABASE=ide_db -e MYSQL_ROOT_PASSWORD=root -p 127.0.0.1:8889:3306 -d mysql:8.0
	( cd tests/test_data/mysite ; poetry run python3 manage.py test )


.PHONY: publish
publish: test  ## Publish the package to PyPI.
	poetry build && \
	poetry publish && \
	\
	git tag v$$(cat pyproject.toml | grep "# publish: version" | sed 's/[^0-9.]*//g') && \
	git push origin --tags
