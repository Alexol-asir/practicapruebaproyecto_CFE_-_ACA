# Cuenta las palabras de un fichero de HDFS y guarda el resultado en HDFS.
# Además guarda qué máquina ha procesado cada trozo, para demostrar el reparto.
import socket
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("wordcount").getOrCreate()
sc = spark.sparkContext

# Borrar resultados anteriores para poder lanzarlo varias veces
hadoop = sc._jvm.org.apache.hadoop
fs = hadoop.fs.FileSystem.get(sc._jsc.hadoopConfiguration())
fs.delete(hadoop.fs.Path("/resultados"), True)

# Leer el fichero de HDFS partido en 4 trozos
lineas = sc.textFile("/datos/entrada.txt", minPartitions=4)

# Contar las palabras
conteo = (lineas.flatMap(lambda linea: linea.split())
                .map(lambda palabra: (palabra.lower(), 1))
                .reduceByKey(lambda a, b: a + b))
conteo.saveAsTextFile("/resultados/wordcount")

# Qué máquina ha procesado cada trozo
def quien(numero, trozo):
    cuantas = sum(1 for _ in trozo)
    yield "trozo %d: %d lineas procesadas en %s" % (numero, cuantas, socket.gethostname())

reparto = lineas.mapPartitionsWithIndex(quien).collect()
sc.parallelize(reparto, 1).saveAsTextFile("/resultados/reparto")

print("===== REPARTO =====")
for linea in reparto:
    print(linea)

spark.stop()
