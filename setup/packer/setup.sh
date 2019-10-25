#!/usr/bin/env bash

set -eux

PACKERFILE=/nfcmusik/setup/packer/packer.json

GOROOT=/usr/lib/go-1.12
GOPATH=$HOME/work

PATH=$PATH:$GOROOT/bin:$GOPATH/bin

function install_packer() {
  local version="$1"

  curl --remote-name --silent --show-error "https://releases.hashicorp.com/packer/${version}/packer_${version}_linux_amd64.zip"
  unzip "packer_${version}_linux_amd64.zip"
  rm -f "packer_${version}_linux_amd64.zip"
  sudo mv packer /usr/local/bin
}

function build_packer_arm_builder_plugin() {
  local src_dir="${GOPATH}/src/github.com/solo-io/packer-builder-arm-image"
  mkdir -p "$(dirname "${src_dir}")"

  if [[ ! -d "${src_dir}" ]] ; then
    git clone https://github.com/solo-io/packer-builder-arm-image.git "${src_dir}"
  fi
  pushd "${src_dir}"

  # NOTE Temporary fix; can be removed one the branch's accompanying PR is reviewd and merged
  if ! git ls-remote --exit-code fork &> /dev/null ; then
    git remote add fork https://github.com/croesnick/packer-builder-arm-image.git
  fi
  git pull fork feature/param-mount_path

  go build
  popd

  sudo mv "${src_dir}/packer-builder-arm-image" /usr/local/bin/
}

function build_rpi_image() {
  PACKER_LOG_FILE=$(mktemp)
  sudo PACKER_LOG=1 packer build "${PACKERFILE}" | tee "${PACKER_LOG_FILE}"

  BUILD_NAME=$(grep -Po "(?<=Build ').*(?=' finished.)" "${PACKER_LOG_FILE}")
  IMAGE_PATH=$(grep -Po "(?<=--> ${BUILD_NAME}: ).*" "${PACKER_LOG_FILE}")

  sudo mv "/home/vagrant/${IMAGE_PATH}" "/nfcmusik/build/nfcmusik-rpi-arm.img"
}

sudo apt-get update -qq
sudo apt-get -q -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" dist-upgrade
sudo apt-get -q -y install \
  curl \
  gcc \
  git \
  golang-1.12-go \
  kpartx \
  python3 \
  python3-pip \
  qemu-user-static \
  unzip

sudo pip3 install --system ansible
go get -u github.com/golang/dep/cmd/dep

install_packer '1.3.5'
build_packer_arm_builder_plugin
build_rpi_image
