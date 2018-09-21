SHELL = bash

CACHE_FILE = _data/gener_yaml.cache.jsonl

YAML_FILES= _data/dependency_parsing.yaml

$(YAML_FILES) : _data/%.yaml : _data/%.yaml.template _data/gener_yaml.py
	_data/gener_yaml.py \
		--yaml-template $< --cache-fname $(CACHE_FILE) > $@

serve: $(YAML_FILES)
	jekyll serve

build: $(YAML_FILES)
	jekyll build

clean:
	rm -rf _site $(YAML_FILES)

clean_cache:
	rm -rf $(CACHE_FILE)

