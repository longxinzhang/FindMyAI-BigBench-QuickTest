# 在这个文件中，我们先从建立好的数据库中抽取其他大语言模型对bigbench题目给的答案
# 然后将LLM的答案和标准答案，发送给GPT-4，让更高级的大语言模型对结果进行判断
# 随后根据提示词出的结果将被写入到PSQL的结果一栏中等待后续使用。
#Note: The openai-python library support for Azure OpenAI is in preview.
import os
import psycopg2
import openai
from tqdm import tqdm
import time

# 准备OpenAI连接
openai.api_type = "azure"
openai.api_base = "https://openai-api-fma.openai.azure.com/"
openai.api_version = "2023-03-15-preview"
openai.api_key = "123123123"

# PostgreSQL数据库连接参数
connection_parameters = {
    "host": "fma-bb-quicktest-find-my-ai-quick-test.aivencloud.com",
    "port": "27618",
    "database": "defaultdb",
    "user": "avnadmin",
    "password": "123123123",
    "sslmode": "require"
}

# 连接到PostgreSQL数据库
conn = psycopg2.connect(**connection_parameters)
cursor = conn.cursor()

# 执行查询，获取category为1_digit_addition的所有行并写入psql_data中
cursor.execute("SELECT * FROM bigbench_2 WHERE category = '1_digit_addition' limit 100;")
results = cursor.fetchall()
psql_data = []
for row in results:
    psql_data.append({"number": row[0], "category": row[1], "question": row[2], "answer": row[3], "chatglm_130b_answer": row[4]})

# 调用openai服务并将结果更新对应表单
for psql_question in tqdm(psql_data, desc="处理问题进度"):
    input_text = "所以：\n[Q] " + psql_question['question'] + "\n[A] " + psql_question['chatglm_130b_answer'] + "\n[Target] " + psql_question['answer'] + "\n[Judgement] \n[Note]"
    
    response = openai.ChatCompletion.create(
        engine="wwzx-gpt-4-8k",
        messages=[
            {"role":"system","content":"You are a helpful AI assistant. 你是一个数据专家，你能判断大语言模型是否根据问题[Q]给出了正确的结果[A]，同时还有参考答案[Target]。在[judgement]里，正确你打1分，错误你打0分，不对也不错0.5分。如果你有备注内容，写在[Note]后面。只有在出现0.5分的时候做[Note]解释，只给Judgement即可。"},{"role":"user","content":"[Q] What is 1+1? \n[A] 2. \n[Target] 2"},{"role":"assistant","content":"[Judgement] 1\n[Note]"},{"role":"user","content":"[Q] What is 2+3? \n[A] 4.\n[Target] 5"},{"role":"assistant","content":"[Judgement] 0\n[Note]"},{"role":"user","content":"[Q] What is pi?\n[A] 3.14.\n[Target] 3.1415926..."},{"role":"assistant","content":"[Judgement] 0.5\n[Note] pi=3.14 并非绝对正确答案，数学计算应根据题目要求确定省略多少位。"},{"role":"user","content":"所以：  \n[Q] 如果一个圆的半径为5，求它的周长。  \n[A]  周长 ≈ 31.42  \n[Target] 31.415926  \n[Judgement]   \n[Note] "},
            {"role": "user", "content": input_text}
        ],
        temperature=0.7,
        max_tokens=800,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None
    )

    # 提取返回词典里的最后一个词典的"content"值
    output_content = response.choices[0].message["content"]
    print("ID:"+f"{psql_question['number']}" +",question:"+psql_question['question']+"，chatglm的答案是："+psql_question['chatglm_130b_answer']+" Target:" +psql_question['answer'])
    print(output_content)

    # 更新PSQL数据，表中id对应psql_data里的number
    update_query = f"UPDATE bigbench_2 SET chatgpt_35_answer = %s WHERE id = %s;"
    cursor.execute(update_query, (output_content, psql_question['number']))
    time.sleep(5)  # 暂停5秒


conn.commit()
print("psql bigbench_2 chatgpt_35_answer已更新")

#关闭数据库连接
print("完成了，下班！")
cursor.close()
conn.close()


