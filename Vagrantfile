# Práctica 1 - Clúster Big Data (HDFS + Spark)
#   master  -> 192.168.56.20
#   worker1 -> 192.168.56.21
#   worker2 -> 192.168.56.22
#
# Vagrant crea las 3 máquinas con su red privada, escritorio XFCE y teclado en castellano.
# Ansible se ejecuta en el anfitrión (terminal de Ubuntu en WSL) y configura las máquinas.

BOX = "bento/ubuntu-24.04"

# Clave pública de quien hace el vagrant up (la de su Ubuntu).
# Se mete en las 3 máquinas para poder entrar con: ssh vagrant@192.168.56.20
CLAVE_PUB = File.expand_path("~/.ssh/id_ed25519.pub")
CLAVE     = File.exist?(CLAVE_PUB) ? File.read(CLAVE_PUB).strip : ""

MI_CLAVE = <<-SHELL
  if [ -n "#{CLAVE}" ] && ! grep -qF "#{CLAVE}" /home/vagrant/.ssh/authorized_keys; then
    echo "#{CLAVE}" >> /home/vagrant/.ssh/authorized_keys
  fi
SHELL

# Escritorio ligero XFCE y teclado en castellano
ESCRITORIO = <<-SHELL
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    xserver-xorg xfce4 xfce4-terminal lightdm lightdm-gtk-greeter \
    adwaita-icon-theme dbus-x11 keyboard-configuration console-setup

  cat > /etc/default/keyboard <<EOK
XKBMODEL="pc105"
XKBLAYOUT="es"
XKBVARIANT=""
XKBOPTIONS=""
BACKSPACE="guess"
EOK
  localectl set-x11-keymap es || true
  setupcon --force 2>/dev/null || true

  # Contraseña para entrar al escritorio: usuario vagrant / contraseña vagrant
  echo "vagrant:vagrant" | chpasswd

  systemctl set-default graphical.target
  systemctl restart lightdm
SHELL

Vagrant.configure("2") do |config|
  config.vm.box = BOX
  config.vm.box_check_update = false

  # No hace falta compartir la carpeta del proyecto con las máquinas
  # (Ansible se lanza desde el anfitrión) y desde WSL da problemas
  config.vm.synced_folder ".", "/vagrant", disabled: true

  # Los workers van primero para que el master se cree el último
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
        vb.name   = "bigdata-#{nombre}"
        vb.memory = 2560
        vb.cpus   = datos[:cpus]
        vb.gui    = true    # abre la ventana con el escritorio
        vb.customize ["modifyvm", :id, "--graphicscontroller", "vmsvga", "--vram", "64"]
      end

      # Tu clave SSH
      nodo.vm.provision "shell", inline: MI_CLAVE

      # Escritorio y teclado
      nodo.vm.provision "shell", inline: ESCRITORIO

      # Ansible: solo se lanza desde el master (el último que se crea),
      # y configura las tres máquinas de una pasada (limit = "all")
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
