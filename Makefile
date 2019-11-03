IMAGE = build/nfcmusik-rpi-arm\.img

.PHONY: flash build-image clean requirements

flash :
	flash --userdata setup/image/config.yml $(IMAGE)

build-image : requirements
	vagrant up --provision
	vagrant halt

clean :
	vagrant destroy --force
	rm -f ${IMAGE}

requirements :
	pipenv lock --requirements > requirements.txt
