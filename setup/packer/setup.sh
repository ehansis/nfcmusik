#!/usr/bin/env bash

set -eux

GOROOT=/usr/lib/go
GOPATH=$HOME/work
PATH=$PATH:$GOROOT/bin:$GOPATH/bin

function install_packer() {
  local version="$1"

  curl --remote-name --silent --show-error "https://releases.hashicorp.com/packer/${version}/packer_${version}_linux_amd64.zip"
  unzip "packer_${version}_linux_amd64.zip"
  sudo mv packer /usr/local/bin
  rm -f "packer_${version}_linux_amd64.zip"
}

function build_packer_arm_builder_plugin() {
  mkdir -p "${GOPATH}/src/github.com/solo-io/"
  pushd "${GOPATH}/src/github.com/solo-io/"

  git clone https://github.com/solo-io/packer-builder-arm-image.git packer-builder-arm-image
  pushd ./packer-builder-arm-image
  go get -d -v
  go build

  popd
  popd
}

# Update the system
sudo apt-get update -qq
sudo apt-get install -y software-properties-common

# Add the golang repo
sudo add-apt-repository --yes ppa:gophers/archive

# Install required packages
sudo apt-get update
sudo apt-get install -y \
  curl \
  gcc \
  git \
  golang-go \
  kpartx \
  qemu-user-static \
  unzip

go get -u github.com/golang/dep/cmd/dep
install_packer '1.4.4'
packer_arm_builder_plugin_dir="$( build_packer_arm_builder_plugin )"

mkdir -p /home/vagrant/.packer.d/plugins
cp "${packer_arm_builder_plugin_dir}/packer-builder-arm-image/packer-builder-arm-image" /home/vagrant/.packer.d/plugins/

PACKER_LOG=$(mktemp)
packer build "${PACKERFILE}" | tee "${PACKER_LOG}"

BUILD_NAME=$(grep -Po "(?<=Build ').*(?=' finished.)" ${PACKER_LOG})
IMAGE_PATH=$(grep -Po "(?<=--> ${BUILD_NAME}: ).*" ${PACKER_LOG})
rm -f "${PACKER_LOG}"

# If the new image is there, copy it out or throw an error
if [[ -f /home/vagrant/${IMAGE_PATH} ]]; then
  sudo cp "/home/vagrant/${IMAGE_PATH}" "/nfcmusik/${IMAGE_PATH%/image}.img"
else
  echo "Error: Unable to find build artifact."
  exit
fi
