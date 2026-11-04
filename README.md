# Práctica 1 – Clúster Big Data

Repositorio: https://github.com/Alexol-asir/practicapruebaproyecto_CFE_-_ACA

## Qué hemos montado

Un clúster de 3 máquinas virtuales que trabajan juntas:

- **master** (192.168.56.20): tiene el NameNode de HDFS y el Spark Master.
- **worker1** (192.168.56.21) y **worker2** (192.168.56.22): cada uno tiene un DataNode y un Spark Worker.

HDFS guarda los ficheros repartidos entre los dos workers, con 2 copias de cada uno. Spark reparte los trabajos entre los dos workers.

Vagrant crea las máquinas, Ansible las configura y los programas (HDFS y Spark) van dentro de contenedores Docker. Todo se levanta con un solo `vagrant up`.

## Archivos

- `Vagrantfile`: crea las 3 máquinas y al final lanza Ansible.
- `site.yml`: dice qué rol va a cada máquina.
- `group_vars/all.yml`: las variables (IPs, imágenes de Docker, número de copias...).
- `roles/common`: lo que llevan las 3 máquinas (Docker, nombres de las máquinas y configuración de HDFS).
- `roles/master`: los contenedores del master, el fichero de prueba y el trabajo de Spark.
- `roles/worker`: los contenedores de los workers.

## Lo que hace falta

Lo lanzamos desde la terminal de Ubuntu de Windows (WSL), con Vagrant, Ansible y VirtualBox instalados, y con el plugin `virtualbox_WSL2` de Vagrant.

## Levantar el clúster

Desde la carpeta del proyecto:

```
vagrant up
```

Tarda un rato la primera vez. Cuando acaba se pueden ver las webs desde el navegador:

- HDFS: http://192.168.56.20:9870 (en la pestaña Datanodes salen los 2 workers)
- Spark: http://192.168.56.20:8080 (salen los 2 workers como ALIVE)

## Subir un fichero a HDFS

El fichero de prueba ya lo deja Ansible en el master. Para subirlo a HDFS:

```
ssh vagrant@192.168.56.20 "docker exec namenode hdfs dfs -mkdir -p /datos && docker exec -i namenode hdfs dfs -put -f - /datos/entrada.txt < /opt/cluster/datos/entrada.txt"
```

## Comprobar que está replicado

```
ssh vagrant@192.168.56.20 "docker exec namenode hdfs fsck /datos/entrada.txt -files -blocks -locations"
```

Tiene que salir `replication=2` y las IPs de los dos workers. Eso quiere decir que hay una copia en cada uno.

## Lanzar el trabajo de Spark

Es un contador de palabras: cuenta cuántas veces sale cada palabra del fichero. Además dice qué worker ha hecho cada trozo del trabajo.

```
ssh vagrant@192.168.56.20 "docker exec spark-master /opt/spark/bin/spark-submit /opt/spark/work-dir/trabajos/wordcount.py 2>/dev/null"
```

Al final sale algo así, con trozos hechos por los dos workers:

```
===== REPARTO =====
trozo 0: 3 lineas procesadas en worker2
trozo 1: 1 lineas procesadas en worker1
trozo 2: 2 lineas procesadas en worker2
trozo 3: 2 lineas procesadas en worker1
```

El resultado se guarda en HDFS. Para verlo:

```
ssh vagrant@192.168.56.20 "docker exec namenode hdfs dfs -cat '/resultados/wordcount/*' '/resultados/reparto/*'"
```

## Si se cae un worker

Apagamos el worker1:

```
vagrant halt worker1
```

Y leemos el fichero de HDFS:

```
ssh vagrant@192.168.56.20 "docker exec namenode hdfs dfs -cat /datos/entrada.txt"
```

Sale entero, porque se lee la copia que hay en worker2. Para volver a encenderlo:

```
vagrant up worker1
```

## Empezar de cero

```
vagrant destroy -f
vagrant up
```

Después hay que volver a subir el fichero a HDFS antes de lanzar el trabajo de Spark, porque las máquinas son nuevas y HDFS está vacío.

## Todo seguido, comando a comando

Desde la terminal de Ubuntu, en la carpeta del proyecto. Lanzar cada comando y esperar a que acabe antes del siguiente.

1. Levantar el clúster:

```
vagrant up
```

2. Mirar las webs en el navegador: http://192.168.56.20:9870 (2 Datanodes) y http://192.168.56.20:8080 (2 workers ALIVE).

3. Subir el fichero a HDFS:

```
ssh vagrant@192.168.56.20 "docker exec namenode hdfs dfs -mkdir -p /datos && docker exec -i namenode hdfs dfs -put -f - /datos/entrada.txt < /opt/cluster/datos/entrada.txt"
```

4. Comprobar las 2 copias:

```
ssh vagrant@192.168.56.20 "docker exec namenode hdfs fsck /datos/entrada.txt -files -blocks -locations"
```

5. Lanzar el trabajo de Spark:

```
ssh vagrant@192.168.56.20 "docker exec spark-master /opt/spark/bin/spark-submit /opt/spark/work-dir/trabajos/wordcount.py 2>/dev/null"
```

6. Ver el resultado del contador, guardado en HDFS (cada palabra y las veces que sale, de más a menos):

```
ssh vagrant@192.168.56.20 "docker exec namenode hdfs dfs -cat '/resultados/wordcount/*'" | sort -t' ' -k2,2nr
```

Y qué worker ha hecho cada trozo:

```
ssh vagrant@192.168.56.20 "docker exec namenode hdfs dfs -cat '/resultados/reparto/*'"
```

7. Apagar un worker:

```
vagrant halt worker1
```

8. Comprobar que el fichero se sigue leyendo:

```
ssh vagrant@192.168.56.20 "docker exec namenode hdfs dfs -cat /datos/entrada.txt"
```

9. Volver a encender el worker:

```
vagrant up worker1
```

Si se cambia algún archivo del proyecto (por ejemplo el texto de `entrada.txt`), para aplicarlo sin borrar las máquinas:

```
vagrant provision master --provision-with ansible
```

Después hay que volver a subir el fichero a HDFS, comprobar sus copias y lanzar otra vez el trabajo de Spark, con los mismos comandos de arriba.

Si al entrar por ssh avisa de que la "host key" ha cambiado (pasa después de borrar y crear las máquinas otra vez):

```
ssh-keygen -R 192.168.56.20
```
