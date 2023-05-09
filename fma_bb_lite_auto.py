import json
import psycopg2
import os
import glob
from tqdm import tqdm

# 遍历目录及其子目录中的所有JSON文件
def load_json_files(root_dir):
    json_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith("task.json"):
                json_files.append(os.path.join(root, file))
    return json_files

#把这个目录下的所有json都存入psql
root_dir = "/Users/zhanglongxin/Desktop/Find My AI/code/BIG-bench-main/bigbench/benchmark_tasks/bbq_lite_json/"

# 加载所有JSON文件
json_files = load_json_files(root_dir)

# 连接到PostgreSQL服务器
conn = psycopg2.connect(
    host="fma-bb-quicktest-find-my-ai-quick-test.aivencloud.com",
    port="27618",
    database="defaultdb",
    user="avnadmin",
    password="111",
    sslmode="require"
)

print("Aiven PSQL is connected!")

# 创建一个表来存储题目和答案
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS bigbench_lite (
    id SERIAL PRIMARY KEY,
    category TEXT NOT NULL,
    example_input_prefix TEXT NOT NULL,
    question TEXT NOT NULL,
    target TEXT NOT NULL,
    LLM_answer TEXT NOT NULL
)
""")
print("正在创建table，若有将跳过")
conn.commit()

# 遍历JSON文件，读取文件内容并插入到PostgreSQL表中
for json_file in json_files:
    with open(json_file, 'r') as f:
        data = json.load(f)
    print(f"Loaded JSON file: {json_file}")

    category = data["name"]
    LLM_answer = ""
    example_input_prefix = json.dumps(data.get("example_input_prefix", "{}"))

    # 遍历JSON对象中的题目，将题目和答案插入到PostgreSQL表中
    for example in tqdm(data["examples"], desc="处理示例"):
        comment = json.dumps(example.get("comment","{}"))
        question = example["input"]
        target = json.dumps(example.get("target_scores","{}"))
        print(f"正在写入问题{question}+答案{target}")
        cursor.execute(
            "INSERT INTO bigbench_lite (category, example_input_prefix, question, target, LLM_answer) VALUES (%s, %s ,%s, %s, %s)",
            (category, example_input_prefix, question, target, LLM_answer)
        )
        print("**写入完成，执行下一个**")

    # 提交事务
    conn.commit()
    print("All task finished!")

# 关闭数据库连接
cursor.close()
conn.close()
