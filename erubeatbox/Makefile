DEV := auto
# Connect is here because one of my Macs thinks my monitor is a good thing to connect to.
CONNECT := mpremote connect $(DEV)

install: install-libs
	$(CONNECT) + cp -rv fs/* :.

install-libs:
	$(CONNECT) + ls :lib/picozero || $(CONNECT) + mip install github:RaspberryPiFoundation/picozero
