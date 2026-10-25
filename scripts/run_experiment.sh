#!/usr/bin/env bash
# Compile and run the inverted-index MapReduce experiment on Hadoop.
set -euo pipefail

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=${HADOOP_HOME:-$HOME/hadoop}
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export PATH=$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

DOCS="$ROOT/data/documents"
if [[ $(find "$DOCS" -maxdepth 1 -type f -name 'document*.txt' | wc -l) -lt 10 ]]; then
  python3 scripts/download_documents.py
fi

echo "== 1. Compile =="
rm -rf build
mkdir -p build
javac -encoding UTF-8 -cp "$(hadoop classpath)" -d build src/InvertedIndex.java
jar cf inverted-index.jar -C build .

echo "== 2. Prepare HDFS input =="
hdfs dfs -rm -r -f -skipTrash /lab2 >/dev/null 2>&1 || true
hdfs dfs -mkdir -p /lab2/input
hdfs dfs -put -f "$DOCS"/document*.txt /lab2/input/
hdfs dfs -put -f data/stopwords.txt /lab2/stopwords.txt
echo "Documents in HDFS: $(hdfs dfs -ls /lab2/input | grep -c 'document.*txt')"
hdfs dfs -ls -h /lab2/input

echo "== 3. Run MapReduce job =="
hadoop jar inverted-index.jar InvertedIndex \
  /lab2/input /lab2/output /lab2/stopwords.txt

echo "== 4. Show selected index entries =="
RESULT=/lab2/output/part-r-00000
mkdir -p results
hdfs dfs -getmerge "$RESULT" results/inverted_index.txt
for word in hadoop mapreduce data protocol server job index search; do
  echo "--- $word ---"
  grep -E "^${word}[[:space:]]" results/inverted_index.txt || echo "(not found)"
done

echo "== 5. Output summary =="
echo "Index entries: $(wc -l < results/inverted_index.txt)"
echo "HDFS output: $RESULT"
