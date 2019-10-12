IMAGE = https\://github\.com/hypriot/image-builder-rpi/releases/download/v1\.11\.1/hypriotos-rpi-v1\.11\.1\.img\.zip

.PHONY: flash

flash:
	flash --userdata setup/image/config.yml --bootconf setup/image/boot.txt $(IMAGE)
