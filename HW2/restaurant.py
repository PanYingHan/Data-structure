import os
import asyncio
import pandas as pd
from dotenv import load_dotenv
import io


from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.agents.web_surfer import MultimodalWebSurfer

load_dotenv()

async def process_food_data(chunk, start_idx, total_records, model_client, termination_condition):
    """
    處理單一批次的餐廳數據：
      - 轉成字典格式
      - 讓 AI 代理人分析餐廳數據，並提供分析結果
    """
    chunk_data = chunk.to_dict(orient='records')
    prompt = (
        f"目前正在處理第 {start_idx} 至 {start_idx + len(chunk) - 1} 筆資料（共 {total_records} 筆）。\n"
        f"統計摘要如下：\n{chunk_data}\n\n"
        "請回答下列問題：\n"
    "1. 哪一種類型的餐廳最受顧客青睞？\n"
    "2. 根據顧客評分，哪個區域的餐廳評價最好？\n"
    "3. 哪個價格區間的餐廳評價較高？\n"
    "4. 根據熱量等級與餐廳類型，您會建議顧客選擇什麼樣的餐廳？\n"
    "5. 根據餐廳資料提供哪些飲食建議，特別是高熱量、高價格或低評價的餐廳？\n"
    )
    local_data_agent = AssistantAgent("data_agent", model_client)
    local_web_surfer = MultimodalWebSurfer("web_surfer", model_client)
    local_assistant = AssistantAgent("assistant", model_client)
    local_user_proxy = UserProxyAgent("user_proxy")
    local_team = RoundRobinGroupChat(
        [local_data_agent, local_web_surfer, local_assistant, local_user_proxy],
        termination_condition=termination_condition
    )
    
    messages = []
    async for event in local_team.run_stream(task=prompt):
        if isinstance(event, TextMessage):
            print(f"[{event.source}] => {event.content}\n")
            messages.append({
                "batch_start": start_idx,
                "batch_end": start_idx + len(chunk) - 1,
                "source": event.source,
                "content": event.content,
                "type": event.type,
                "prompt_tokens": event.models_usage.prompt_tokens if event.models_usage else None,
                "completion_tokens": event.models_usage.completion_tokens if event.models_usage else None
            })
    return messages

async def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("請檢查 .env 檔案中的 GEMINI_API_KEY。")
        return

    model_client = OpenAIChatCompletionClient(
        model="gemini-2.0-flash",
        api_key=api_key,
    )
    
    termination_condition = TextMentionTermination("exit")
    
    csv_file_path = "restaurant_data.csv"
    chunk_size = 1000
    chunks = list(pd.read_csv(csv_file_path, chunksize=chunk_size))
    total_records = sum(chunk.shape[0] for chunk in chunks)
    
    tasks = list(map(
        lambda idx_chunk: process_food_data(
            idx_chunk[1],
            idx_chunk[0] * chunk_size,
            total_records,
            model_client,
            termination_condition
        ),
        enumerate(chunks)
    ))
    
    results = await asyncio.gather(*tasks)
    all_messages = [msg for batch in results for msg in batch]
    
    df_log = pd.DataFrame(all_messages)
    output_file = "restaurant_analysis_result.csv"
    df_log.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"已將所有分析結果輸出為 {output_file}")

if __name__ == '__main__':
    asyncio.run(main()) 