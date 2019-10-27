# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-19.04"
  config.vm.box_version = "201906.18.0"
  config.vm.box_check_update = true
  config.vm.synced_folder ".", "/nfcmusik"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "1024"
  end

  config.vm.provision "setup", type: "shell",
                               path: "setup/packer/setup.sh",
                               privileged: false,
                               env: { "PACKERFILE" => "/nfcmusik/setup/packer/packer.json" }
end
