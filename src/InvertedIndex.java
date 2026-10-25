import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.input.FileSplit;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

/**
 * Builds an inverted index over a directory of English text documents.
 *
 * <p>Each reducer key is a word. Its value lists the number of occurrences in
 * every document containing that word, followed by the total frequency.
 */
public final class InvertedIndex extends Configured implements Tool {
  private static final Pattern WORD_PATTERN =
      Pattern.compile("[A-Za-z0-9]+(?:'[A-Za-z]+)?");

  public static final class IndexMapper extends Mapper<Object, Text, Text, Text> {
    private final Text word = new Text();
    private final Text documentCount = new Text();
    private final Set<String> stopWords = new HashSet<>();
    private String documentId;

    @Override
    protected void setup(Context context) throws IOException {
      FileSplit split = (FileSplit) context.getInputSplit();
      documentId = split.getPath().getName();

      Configuration conf = context.getConfiguration();
      Path stopWordPath = new Path(conf.get("inverted.index.stopwords"));
      FileSystem fileSystem = stopWordPath.getFileSystem(conf);
      try (BufferedReader reader = new BufferedReader(
          new InputStreamReader(fileSystem.open(stopWordPath), StandardCharsets.UTF_8))) {
        String line;
        while ((line = reader.readLine()) != null) {
          String entry = line.trim().toLowerCase(Locale.ROOT);
          if (!entry.isEmpty() && !entry.startsWith("#")) {
            stopWords.add(entry);
          }
        }
      }
    }

    @Override
    protected void map(Object key, Text value, Context context)
        throws IOException, InterruptedException {
      Matcher matcher = WORD_PATTERN.matcher(value.toString());
      while (matcher.find()) {
        String token = matcher.group().toLowerCase(Locale.ROOT);
        if (stopWords.contains(token)) {
          continue;
        }
        word.set(token);
        documentCount.set(documentId + ":1");
        context.write(word, documentCount);
      }
    }
  }

  public static final class IndexCombiner extends Reducer<Text, Text, Text, Text> {
    private final Text output = new Text();

    @Override
    protected void reduce(Text key, Iterable<Text> values, Context context)
        throws IOException, InterruptedException {
      Map<String, Integer> perDocument = new TreeMap<>();
      for (Text value : values) {
        String item = value.toString();
        int separator = item.lastIndexOf(':');
        String documentId = item.substring(0, separator);
        int count = Integer.parseInt(item.substring(separator + 1));
        perDocument.merge(documentId, count, Integer::sum);
      }
      for (Map.Entry<String, Integer> entry : perDocument.entrySet()) {
        output.set(entry.getKey() + ":" + entry.getValue());
        context.write(key, output);
      }
    }
  }

  public static final class IndexReducer extends Reducer<Text, Text, Text, Text> {
    private final Text output = new Text();

    @Override
    protected void reduce(Text key, Iterable<Text> values, Context context)
        throws IOException, InterruptedException {
      Map<String, Integer> perDocument = new TreeMap<>();
      int total = 0;
      for (Text value : values) {
        String item = value.toString();
        int separator = item.lastIndexOf(':');
        String documentId = item.substring(0, separator);
        int count = Integer.parseInt(item.substring(separator + 1));
        perDocument.merge(documentId, count, Integer::sum);
        total += count;
      }

      StringBuilder index = new StringBuilder();
      for (Map.Entry<String, Integer> entry : perDocument.entrySet()) {
        index.append(entry.getKey())
            .append(':')
            .append(entry.getValue())
            .append(';');
      }
      index.append("total:").append(total);
      output.set(index.toString());
      context.write(key, output);
    }
  }

  @Override
  public int run(String[] args) throws Exception {
    if (args.length != 3) {
      System.err.println(
          "Usage: InvertedIndex <input-directory> <output-directory> <stopwords-file>");
      return 2;
    }

    Configuration conf = getConf();
    conf.set("inverted.index.stopwords", args[2]);

    Job job = Job.getInstance(conf, "document inverted index");
    job.setJarByClass(InvertedIndex.class);
    job.setMapperClass(IndexMapper.class);
    job.setCombinerClass(IndexCombiner.class);
    job.setReducerClass(IndexReducer.class);
    job.setOutputKeyClass(Text.class);
    job.setOutputValueClass(Text.class);

    // A single reducer produces a globally sorted index in one output file.
    job.setNumReduceTasks(1);

    FileInputFormat.addInputPath(job, new Path(args[0]));
    FileOutputFormat.setOutputPath(job, new Path(args[1]));

    return job.waitForCompletion(true) ? 0 : 1;
  }

  public static void main(String[] args) throws Exception {
    int exitCode = ToolRunner.run(new Configuration(), new InvertedIndex(), args);
    System.exit(exitCode);
  }
}
