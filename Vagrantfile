# Práctica 1 - Clúster Big Data (HDFS + Spark)
# Vagrant levanta las 3 máquinas y su red privada.
# Ansible (desde el PC, con WSL) las configura y arranca los contenedores Docker.

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  config.vm.box_check_update = false

  # Los workers van primero para que el master se cree el último.
  # Así, cuando el master lanza Ansible, las tres máquinas ya existen.
  nodos = {
    "worker1" => { ip: "192.168.56.21", cpus: 1 },
    "worker2" => { ip: "192.168.56.22", cpus: 1 },
    "master"  => { ip: "192.168.56.20", cpus: 2 }
  }

  nodos.each do |nombre, datos|
    config.vm.define nombre do |nodo|
      nodo.vm.hostname = nombre
      nodo.vm.network "private_network", ip: datos[:ip]

      nodo.vm.provider "virtualbox" do |vb|
        vb.name         = "bigdata-#{nombre}"
        vb.memory       = 2048
        vb.cpus         = datos[:cpus]
        vb.linked_clone = true   # las 3 VMs comparten el disco base, ocupa menos
      end

      # Ansible se lanza una sola vez, desde el master, contra las tres máquinas
      if nombre == "master"
        nodo.vm.provision "ansible" do |ansible|
          ansible.playbook = "site.yml"
          ansible.limit    = "all"
          ansible.groups   = {
            "masters"          => ["master"],
            "workers"          => ["worker1", "worker2"],
            "bigdata:children" => ["masters", "workers"]
          }
        end
      end
    end
  end
end
