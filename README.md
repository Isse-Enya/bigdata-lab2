# 大数据管理与分析 实验二 倒排索引

本实验使用 Hadoop MapReduce 为 10 个公开英文技术文档建立倒排索引。每个索引项采用如下格式：

```text
word <document01.txt:n>;<document02.txt:m>;...;<total:N>
```

`n`、`m` 表示该单词在对应文档中的词频，`N` 表示其在全部文档中的总词频。停词表中的单词不进入索引。

## 目录结构

```text
bigdata-lab2/
├── src/InvertedIndex.java           MapReduce 主程序
├── data/stopwords.txt               英文停词表
├── data/documents/                  10 个公开英文文档及来源清单
├── scripts/download_documents.py    文档下载与 HTML 正文提取脚本
├── scripts/run_experiment.sh        编译、上传输入并提交作业
├── scripts/validate_results.py      对全部倒排索引项做独立校验
└── README.md
```

第三方英文文档不纳入版本库；首次运行脚本时会根据 `data/documents/SOURCES.md` 中的公开
URL 自动下载。这样仓库只保留来源说明、可复现脚本和实验结果。

## 运行环境

* Ubuntu 24.04 LTS 64 位
* OpenJDK 11
* Hadoop 3.3.6（伪分布式）
* Python 3（仅用于准备公开文档）

## 运行方法

```bash
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=$HOME/hadoop
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export PATH=$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH

# 首次运行前启动 Hadoop
start-dfs.sh
start-yarn.sh

bash scripts/run_experiment.sh
```

脚本把输入文件上传到 `/lab2/input`，把停词表上传到 `/lab2/stopwords.txt`，作业输出位于
`/lab2/output/part-r-00000`，同时把结果保存为 `results/inverted_index.txt`。

运行完整结果校验：

```bash
python3 scripts/validate_results.py
```

校验脚本使用独立的正则分词和字典计数重新生成全部索引项。全部一致时输出
`PASS: all 8849 index entries match independent counts`。

## 算法说明

1. Mapper 从当前分片路径取得文档名，用正则表达式提取英文单词并转换为小写。
2. Mapper 过滤停词后，为每个单词输出 `<word, document.txt:1>`。
3. Combiner 按文档合并计数，减少 Shuffle 阶段的网络传输量。
4. Reducer 再用有序映射汇总各文档词频，输出“文档计数列表 + total”。
5. 只启动一个 Reduce 任务，使单词键在同一个结果文件中全局有序，便于检索。
