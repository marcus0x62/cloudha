SOURCES=cloudha.py common.py

cloudha.zip: $(SOURCES)
	zip $@ $(SOURCES)