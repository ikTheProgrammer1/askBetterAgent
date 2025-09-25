from openai import OpenAI
import time

# Initialize the synchronous client
client = OpenAI()

def get_capital_synchronously():
    print("-> Asking for the capital of France...")
    start_time = time.time()
    
    # This is a blocking network call. The program waits here.
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "What is the capital of France?"}]
    )
    
    end_time = time.time()
    print(f"✅ Received response in {end_time - start_time:.2f} seconds.")
    return response.choices[0].message.content

# Run the function
get_capital_synchronously()



# from agents import Agent, Runner
# import asyncio

# history_tutor_agent = Agent(
#     name="History Tutor",
#     handoff_description="Specialist agent for historical questions",
#     instructions="I am the History Tutor and have been selected. You provide assistance with historical queries. Explain important events and context clearly.",
# )

# math_tutor_agent = Agent(
#     name="Math Tutor",
#     handoff_description="Specialist agent for math questions",
#     instructions="I am the Math Tutor and have been selected. You provide help with math problems. Explain your reasoning at each step and include examples",
# )

# triage_agent = Agent(
#     name="Triage Agent",
#     instructions="Determine if the user's homework question is about math or history. If the question contains a math problem or a number, hand it off to the Math Tutor. If the question is about historical events, people, or places, hand it off to the History Tutor.",
#     handoffs=[history_tutor_agent, math_tutor_agent]
# )
# async def main():
#     result = await Runner.run(triage_agent, "What is 2+2")
#     print(result.final_output)

# if __name__ == "__main__":
#     asyncio.run(main())

