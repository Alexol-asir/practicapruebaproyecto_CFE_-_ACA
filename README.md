# Práctica 1 y 2 – Clúster Big Data con monitorización

Repositorio: https://github.com/Alexol-asir/practicapruebaproyecto_CFE_-_ACA

La Práctica 1 está marcada con la etiqueta `p1-entrega`. Todo lo de después es la Práctica 2 (monitorización).

## Qué hemos montado

Un clúster de 3 máquinas virtuales que trabajan juntas:

- **master** (192.168.56.20): tiene el NameNode de HDFS y el Spark Master. En la Práctica 2 lleva además Prometheus, Grafana, Alertmanager y json-exporter.
- **worker1** (192.168.56.21) y **worker2** (192.168.56.22): cada uno tiene un DataNode y un Spark Worker.

HDFS guarda los ficheros repartidos entre los dos workers, con 2 copias de cada uno. Spark reparte los trabajos entre los dos workers.

Las tres máquinas llevan también node_exporter (métricas de la máquina) y cAdvisor (métricas de cada contenedor), y Prometheus las lee todas.

Vagrant crea las máquinas, Ansible las configura y los programas van dentro de contenedores Docker. Todo se levanta con un solo `vagrant up`, incluidos el panel de Grafana y las alertas.

## Archivos

- `Vagrantfile`: crea las 3 máquinas y al final lanza Ansible. El master tiene 4 GB de RAM y los workers 2,5 GB.
- `site.yml`: dice qué rol va a cada máquina.
- `group_vars/all.yml`: las variables (IPs, imágenes de Docker, número de copias...).
- `secretos.yml.ejemplo`: plantilla de los secretos (token de Telegram y contraseña de Grafana). El `secretos.yml` de verdad no se sube al repositorio.
- `roles/common`: lo que llevan las 3 máquinas (Docker, nombres de las máquinas y configuración de HDFS).
- `roles/master`: los contenedores del master, el fichero de prueba, el trabajo de Spark y el `metrics.properties` de Spark.
- `roles/worker`: los contenedores de los workers y su `metrics.properties`.
- `roles/exportadores`: node_exporter y cAdvisor en las 3 máquinas.
- `roles/monitorizacion`: Prometheus, Grafana, Alertmanager y json-exporter en el master.
  - `templates/prometheus.yml.j2`: qué lee Prometheus y cada cuánto.
  - `files/reglas/alertas.yml`: las reglas de alerta.
  - `templates/alertmanager.yml.j2`: el envío de alertas a Telegram.
  - `files/json-exporter.yml`: la traducción de las métricas de HDFS.
  - `files/grafana/`: la conexión de Grafana con Prometheus y el cargador de paneles.
  - `files/dashboards/cluster-big-data.json`: el panel «Clúster Big Data».

## Lo que hace falta

Lo lanzamos desde la terminal de Ubuntu de Windows (WSL), con Vagrant, Ansible y VirtualBox instalados, y con el plugin `virtualbox_WSL2` de Vagrant.

Antes del primer `vagrant up` hay que crear el fichero de secretos (ver el apartado «Secretos» más abajo). Sin él, Ansible para y avisa.

## Levantar el clúster

Desde la carpeta del proyecto:

```
vagrant up
```

Tarda un rato la primera vez. Cuando acaba se pueden ver las webs desde el navegador:

- HDFS: http://192.168.56.20:9870 (en la pestaña Datanodes salen los 2 workers)
- Spark: http://192.168.56.20:8080 (salen los 2 workers como ALIVE)
- Las de la monitorización están en el apartado «Monitorización».

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

Después hay que volver a subir el fichero a HDFS antes de lanzar el trabajo de Spark, porque las máquinas son nuevas y HDFS está vacío. Ojo: también se pierden los datos guardados en Prometheus.

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

Si desde WSL no se llega a la red 192.168.56.x (en algún PC nos ha pasado), los mismos comandos funcionan cambiando `ssh vagrant@192.168.56.20 "..."` por `vagrant ssh master -c "..."`.

# Monitorización (Práctica 2)

## Secretos

El token del bot de Telegram y la contraseña de Grafana no se suben al repositorio. Van en `secretos.yml`, que está en el `.gitignore`. Para crearlo:

```
cp secretos.yml.ejemplo secretos.yml
```

Y rellenar en `secretos.yml`:

- `telegram_bot_token`: el token que da @BotFather al crear el bot.
- `telegram_chat_id`: el número del grupo de Telegram que recibe las alertas. Se saca metiendo el bot en el grupo, escribiendo `/start` en el grupo y abriendo `https://api.telegram.org/bot<TOKEN>/getUpdates`. Es un número negativo y va sin comillas.
- `grafana_admin_password`: la contraseña del usuario `admin` de Grafana.

Ansible lo lee en el rol `monitorizacion` y con esos valores genera la configuración de Alertmanager y el docker-compose de Grafana dentro del master.

## Cómo acceder a cada web

Todo se abre desde el navegador de Windows, con el clúster encendido.

- **Grafana (las gráficas):** http://192.168.56.20:3000. Usuario `admin` y la contraseña de `secretos.yml`. Para ver nuestro panel: menú de la izquierda → **Dashboards** → **Clúster Big Data**, o directamente http://192.168.56.20:3000/d/cluster-big-data. Arriba a la derecha se elige el rango de tiempo (por ejemplo «Last 1 hour» o unas horas concretas).
- **Prometheus (los datos y las alertas):** http://192.168.56.20:9090.
  - **Status → Target health** (http://192.168.56.20:9090/targets): cada objetivo que lee Prometheus y si responde (UP) o no (DOWN).
  - **Alerts** (http://192.168.56.20:9090/alerts): las 4 reglas de alerta y su estado (Inactive, Pending o Firing).
  - **Query** (http://192.168.56.20:9090/query): para escribir consultas. Se escribe la consulta, botón **Execute**, y se ve en la pestaña **Table** (el valor ahora) o **Graph** (la gráfica).
- **Alertmanager (los avisos):** http://192.168.56.20:9093. Las alertas que están avisando ahora mismo y a quién se mandan. Los avisos llegan al grupo de Telegram.
- **HDFS:** http://192.168.56.20:9870. Pestaña **Datanodes** para ver los DataNodes vivos.
- **Spark Master:** http://192.168.56.20:8080. Los Spark Workers vivos y los trabajos en marcha y terminados.
- **json-exporter:** http://192.168.56.20:7979. No hace falta abrirlo; es el que traduce las métricas de HDFS para Prometheus.
- **node_exporter:** puerto 9100 de cada máquina (por ejemplo http://192.168.56.21:9100/metrics). Son los datos en bruto; se miran mejor en Grafana.
- **cAdvisor:** puerto 8085 de cada máquina (por ejemplo http://192.168.56.21:8085). No va en el 8080, que es el que tiene por defecto, porque en el master ese puerto ya lo usa la web de Spark Master.

Prometheus, Grafana, Alertmanager y json-exporter van en el master, dentro de una red de Docker propia (`10.20.30.0/24`). Por eso Grafana busca a Prometheus como `http://prometheus:9090` y no como `localhost`. El rango de esa red está fijado a mano: si Docker elige uno de 172.16.0.0/12, puede coincidir con la red de WSL y Vagrant deja de poder entrar en el master.

Los datos de Prometheus (se guardan 60 días), Grafana y Alertmanager están en volúmenes de Docker, así que no se pierden al recrear los contenedores.

Prometheus enseña las horas en UTC (una hora menos que en España en invierno).

## Cambiar las credenciales de Grafana

La contraseña de `secretos.yml` solo se aplica la primera vez que arranca Grafana, cuando su volumen está vacío. Después Grafana la guarda en su base de datos.

- **En un clúster nuevo:** cambiar `grafana_admin_password` en `secretos.yml` antes del `vagrant up`.
- **En un clúster que ya está funcionando:** cambiarla con la herramienta de Grafana y apuntar la nueva también en `secretos.yml`, para que coincidan:

```
vagrant ssh master -c "docker exec grafana grafana cli admin reset-admin-password NUEVA_CONTRASEÑA"
```

## Qué métricas se recogen y cómo

Prometheus lee cada 15 segundos estos objetivos (cada uno lleva la etiqueta `nodo` con el nombre de la máquina):

- `node`: node_exporter de las 3 máquinas. CPU, memoria, disco, red, carga y steal.
- `cadvisor`: cAdvisor de las 3 máquinas. CPU, memoria, red y reinicios de cada contenedor.
- `hdfs`: métricas del NameNode, a través de json-exporter.
- `spark_master` y `spark_workers`: métricas de Spark.
- `prometheus`: el propio Prometheus.

### HDFS

El NameNode publica sus datos en formato JSON en `http://192.168.56.20:9870/jmx`. **json-exporter** lee de ahí el bean `FSNamesystemState` y lo traduce a métricas de Prometheus con nuestros nombres:

- `hdfs_datanodes_vivos` (NumLiveDataNodes)
- `hdfs_datanodes_muertos` (NumDeadDataNodes)
- `hdfs_capacidad_total_bytes` (CapacityTotal)
- `hdfs_capacidad_usada_bytes` (CapacityUsed)
- `hdfs_capacidad_libre_bytes` (CapacityRemaining)
- `hdfs_bloques_subreplicados` (UnderReplicatedBlocks)

Lo elegimos frente al agente JMX porque no hay que tocar el contenedor ni la JVM de Hadoop: usa la web que el NameNode ya tiene, y si json-exporter falla, HDFS no se entera.

### Spark

Spark trae de serie un **PrometheusServlet** que publica sus métricas en su propia web. Se activa con el fichero `metrics.properties` (en `roles/master/files` y `roles/worker/files`), que se monta en los contenedores de Spark. Prometheus lo lee en:

- Spark Master: `http://192.168.56.20:8080/metrics/master/prometheus/`
- Spark Workers: `http://192.168.56.21:8081/metrics/prometheus/` y `http://192.168.56.22:8081/metrics/prometheus/`

Las que usamos:

- `metrics_master_aliveWorkers_Value`: Spark Workers vivos.
- `metrics_master_apps_Value`: aplicaciones Spark en ejecución.

Lo elegimos porque viene con Spark y no necesita ningún agente aparte. Como esa página no dice bien qué formato tiene, en `prometheus.yml` se le indica con `fallback_scrape_protocol: PrometheusText0.0.4` (Prometheus 3 lo exige).

Spark solo lee `metrics.properties` al arrancar. Si se cambia, hay que reiniciar los contenedores `spark-master` y `spark-worker`.

## Panel de Grafana

El panel «Clúster Big Data» se carga solo al arrancar Grafana, desde `roles/monitorizacion/files/dashboards/cluster-big-data.json`. No se configura nada a mano: tras un `vagrant destroy -f && vagrant up` aparece igual. Tiene cuatro filas, y en cada gráfica las líneas llevan el nombre de la máquina (master, worker1 o worker2).

**¿Está vivo?**

- **Estado de cada objetivo:** un recuadro por cada cosa que lee Prometheus (por ejemplo «node · worker1»). Verde UP = responde; rojo CAÍDO = no responde.
- **DataNodes vivos / DataNodes muertos:** los que cuenta el NameNode de HDFS. Lo normal es 2 vivos y 0 muertos.
- **Spark Workers vivos:** los que ve el Spark Master. Lo normal es 2.

**¿Van justos los recursos?**

- **CPU por VM, Memoria usada por VM, Disco usado por VM:** porcentaje usado en cada máquina (de node_exporter).
- **Steal por VM:** tiempo que la máquina quería CPU y el PC no se la dio. En VirtualBox sale siempre a 0, porque VirtualBox no da ese dato.
- **CPU por contenedor:** núcleos de CPU que usa cada contenedor (1 = un núcleo entero), de cAdvisor.
- **Memoria por contenedor:** memoria que usa cada contenedor, de cAdvisor.

**¿Cómo está HDFS?**

- **Capacidad de HDFS:** espacio usado y libre.
- **Uso de HDFS:** porcentaje usado. Verde hasta 70 %, naranja hasta 85 %, rojo a partir de ahí.
- **Bloques sub-replicados:** bloques con menos copias de las debidas. Lo normal es 0.

**¿Qué está haciendo Spark?**

- **Aplicaciones Spark en ejecución:** trabajos en marcha en ese momento.
- **CPU de cada Spark Worker (contenedor):** CPU del contenedor spark-worker de cada worker, que es donde se ejecuta el trabajo.
- **CPU de las VM worker:** CPU de las máquinas worker1 y worker2.

## Alertas

Están en `roles/monitorizacion/files/reglas/alertas.yml`. Alertmanager las manda al grupo de Telegram. Cada una lleva un `for`, una gravedad y una anotación `comprobar_primero` con lo primero que hay que mirar.

- **ObjetivoCaido** (crítica, 1 minuto): algún objetivo de Prometheus deja de responder.
- **HDFSFaltanDataNodes** (crítica, 1 minuto): hay menos de 2 DataNodes vivos.
- **HDFSBloquesSubreplicados** (aviso, 5 minutos): hay bloques con menos copias de las debidas.
- **DiscoLlenoEn24h** (aviso, 30 minutos): según la tendencia de las últimas 6 horas (`predict_linear`), el disco de una máquina se llenará en menos de 24 horas.

Para ver una alerta llegando a Telegram, se apaga a propósito el node_exporter de un worker:

```
vagrant ssh worker1 -c "docker stop node-exporter"
```

En http://192.168.56.20:9090/alerts, **ObjetivoCaido** pasa a Pending y al minuto a Firing, y medio minuto después llega el aviso. Para que vuelva a la normalidad (llega también el aviso de «Resolved»):

```
vagrant ssh worker1 -c "docker start node-exporter"
```

## Cómo reproducir los experimentos

El detalle de cada experimento, con capturas, está en `experimentos`.

Cómo abrir el panel, las consultas y las alertas está explicado en «Cómo acceder a cada web».

Antes de cada experimento conviene comprobar en el panel, en la fila «¿Está vivo?», que todo está en verde.

### Experimento A: ¿se reparte el trabajo?

1. Crear en el master un fichero grande, repitiendo `entrada.txt` hasta que pese 408 MB, y subirlo a HDFS en lugar del pequeño (el trabajo de Spark lee siempre `/datos/entrada.txt`):

```
ssh vagrant@192.168.56.20 "cp /opt/cluster/datos/entrada.txt /tmp/grande.txt && for i in \$(seq 1 15); do cat /tmp/grande.txt /tmp/grande.txt > /tmp/doble.txt && mv /tmp/doble.txt /tmp/grande.txt; done && ls -lh /tmp/grande.txt"
ssh vagrant@192.168.56.20 "docker exec -i namenode hdfs dfs -put -f - /datos/entrada.txt < /tmp/grande.txt"
```

2. Lanzar el trabajo con los 2 workers, apuntando la hora de inicio y de fin:

```
date +%H:%M:%S; ssh vagrant@192.168.56.20 "docker exec spark-master /opt/spark/bin/spark-submit /opt/spark/work-dir/trabajos/wordcount.py 2>/dev/null | tail -8"; date +%H:%M:%S
```

3. Mientras dura, en el panel (rango «Last 15 minutes») bajar a la fila **«¿Qué está haciendo Spark?»**: «Aplicaciones Spark en ejecución» sube a 1 y en «CPU de cada Spark Worker» suben worker1 y worker2. En la fila **«¿Van justos los recursos?»**, «CPU por VM» enseña lo mismo por máquina.

4. Repetir con un solo Spark Worker. Se para el de worker2, se espera a que en http://192.168.56.20:8080 salga solo 1 worker ALIVE (tarda alrededor de un minuto) y se lanza el mismo comando del paso 2:

```
vagrant ssh worker2 -c "docker stop spark-worker"
```

Mientras está parado salta la alerta ObjetivoCaido del worker2, y es lo esperado. Al terminar:

```
vagrant ssh worker2 -c "docker start spark-worker"
```

5. Para dejar otra vez el fichero pequeño en HDFS:

```
ssh vagrant@192.168.56.20 "docker exec -i namenode hdfs dfs -put -f - /datos/entrada.txt < /opt/cluster/datos/entrada.txt"
```

Consultas en Prometheus (http://192.168.56.20:9090/query, pestaña Graph):

```
100 * (1 - avg by (nodo) (rate(node_cpu_seconds_total{mode="idle"}[1m])))
sum by (nodo, name) (rate(container_cpu_usage_seconds_total{name="spark-worker"}[1m]))
```

**Resultado (15/11):** con 2 workers el trabajo tardó 2 min 19 s y los 4 trozos se repartieron 2 y 2, con los dos workers casi al 100 % de CPU. Con 1 worker tardó 2 min 46 s, solo un 20 % más, porque las máquinas comparten la CPU y el disco del mismo PC. Lo que limita es la CPU; la memoria no pasó del 55 %.

### Experimento B: cae un worker

1. Subir el fichero pequeño a HDFS y comprobar que tiene 2 copias (comandos de «Subir un fichero a HDFS» y «Comprobar que está replicado»).
2. Apagar el worker1 apuntando la hora:

```
date +%H:%M:%S; vagrant halt worker1; date +%H:%M:%S
```

3. Apuntar cuándo pasa cada alerta a Pending y a Firing (http://192.168.56.20:9090/alerts, recargando la página), la hora de cada mensaje de Telegram, y cuándo en el panel «DataNodes vivos» baja a 1 (fila «¿Está vivo?») y «Bloques sub-replicados» sube de 0 (fila «¿Cómo está HDFS?»). HDFS tarda unos 10 minutos y medio en dar por muerto un DataNode.
4. Con el worker1 apagado, comprobar que el fichero se sigue leyendo:

```
vagrant ssh master -c "docker exec namenode hdfs dfs -cat /datos/entrada.txt 2>/dev/null | head -5"
```

5. Encender el worker1 y apuntar cuándo se resuelven las alertas y vuelven los bloques a estar bien:

```
date +%H:%M:%S; vagrant up worker1; date +%H:%M:%S
```

Consultas en Prometheus (pestaña Graph):

```
hdfs_datanodes_vivos
hdfs_bloques_subreplicados
up{nodo="worker1"}
ALERTS
```

**Resultado (13/11, en el PC de Carlos):** la alerta de objetivo caído llegó a Telegram en menos de 2 minutos. HDFS tardó unos 10 minutos y 50 segundos en dar el DataNode por muerto y marcar un bloque sub-replicado, y el fichero se siguió leyendo entero desde worker2. Al encender el worker volvió todo a la normalidad.

### Experimento C: línea base y dimensionamiento

1. Dejar el clúster sin hacer nada al menos 30 minutos y apuntar la franja horaria.
2. En el panel, en el botón del reloj de arriba a la derecha, poner en **From** y **To** la hora de inicio y de fin de esa franja y pulsar **Apply time range**. Después, en la fila **«¿Van justos los recursos?»**, anotar la CPU, la memoria y el disco de cada máquina y la CPU y memoria de cada contenedor.
3. Hacer lo mismo con la franja del experimento A y comparar.
4. Lo que consume la propia monitorización en el master (en http://192.168.56.20:9090/query, pestaña **Table**):

```
sum(container_memory_working_set_bytes{nodo="master", name=~"prometheus|grafana|alertmanager|json-exporter"})
sum(rate(container_cpu_usage_seconds_total{nodo="master", name=~"prometheus|grafana|alertmanager|json-exporter"}[5m]))
```

Otras consultas útiles:

```
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
100 * (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})
sum by (nodo, name) (container_memory_working_set_bytes{name!=""})
```

**Resultado (reposo del 13/11 de 20:00 a 21:00, comparado con el experimento A):** en reposo, el master usa un 15-18 % de CPU y un 40 % de memoria, y los workers un 5 % y un 32 %. La monitorización gasta 294 MB y 0,09 núcleos en el master. Con el trabajo, el master llega a 2 GB (53 %), lo que justifica haberlo subido a 4 GB, y los workers a 1 GB (42 %) con la CPU al 100 %: les sobra memoria (bastarían 2 GB) y les falta CPU (convendrían 2).
