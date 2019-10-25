IMAGE = build/nfcmusik-rpi-arm\.img

.PHONY: flash build-image clean

flash :
	flash --config setup/image/config.yml $(IMAGE)

build-image :
	vagrant up --provision
	vagrant halt

clean :
	vagrant destroy --force
	rm -f ${IMAGE}
