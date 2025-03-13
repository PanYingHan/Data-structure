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
    處理單一批次的食物熱量數據：
      - 轉成字典格式
      - 讓 AI 代理人分析熱量攝取，並提供健康建議
      - 搜尋最新的飲食建議，並整合進回覆中
    """
    chunk_data = chunk.to_dict(orient='records')
    prompt = (
        f"目前正在處理第 {start_idx} 至 {start_idx + len(chunk) - 1} 筆資料（共 {total_records} 筆）。\n"
        f"以下為該批次食物熱量數據:\n{chunk_data}\n\n"
        "請根據以上數據提供健康建議，包括：\n"
        "  1. 熱量是否超標，哪些食物需要適量攝取；\n"
        "  2. 根據蛋白質、脂肪、碳水化合物比例，建議如何調整飲食；\n"
        "  3. 搜尋最新的健康飲食建議，並整合進回覆中；\n"
        "  4. 最後提供具體的飲食調整建議和參考資料。\n"
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
    
    csv_file_path = "food_calories.csv"
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
    output_file = "food_analysis_log.csv"
    df_log.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"已將所有分析結果輸出為 {output_file}")

if __name__ == '__main__':
    asyncio.run(main())
