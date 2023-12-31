import os
from dotenv import load_dotenv
import openai

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# Define tasks and their optimal solutions
tasks = {
    "python_snake": {
        "description": "Write a snake game in python",
        "optimal_solution": "..."
    },
    # ...
}

model = "gpt-4"
variation_count = 2
task_run_count = 2

call_limiter = 10
current_call_count = 0

def openai_chat_completion(model, messages, functions=None):
    global current_call_count
    current_call_count = current_call_count+1
    if current_call_count > call_limiter: 
        print("call limit reached")
        return
    
    if functions:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            functions=functions,
        )
        return response['choices'][0]['message']["function_call"]["arguments"] # type: ignore
    else:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
        )
        return response['choices'][0]['message']['content']  # type: ignore

def generate_prompts_for_task(task, model, variation_count):
    prompts = []
    for _ in range(variation_count):
        messages=[
                {"role": "system", "content": "You are a prompt assistant. You are given a task for which you need to generate a prompt that we can later use to request to complete said task."},
                {"role": "user", "content": f"Please provide a prompt for completing the following task: {task['description']}"},
        ]
        response = openai_chat_completion(model, messages)
        prompts.append(response)
    return prompts

def execute_prompts(prompts, model, task_run_count):
    results = {}
    for i, prompt in enumerate(prompts):
        task_results = []
        for i in range(task_run_count):  # Run each task  multiple times
            print(f"execute_prompts: executing prompt {prompt}. Attempt {i}/{task_run_count}")
            messages=[
                # {"role": "system", "content": "if the content contains a tag [CODE} then only return code."},
                {"role": "user", "content": prompt},
            ]
            new_prompt = openai_chat_completion(model, messages)
            task_results.append(new_prompt)
        results[i] = task_results
    return results

def score_task_result(task, result, tasks, model):
    # The scoring logic is as follows:
    # - We will use OpenAI function calling to generate a usefulness score between the result and the optimal solution.
    # - The score will be a value between 0 and 1, where 1 means the result and the optimal solution are identical in terms of usefulness.
    # This approach takes into account the USEFULNESS of the solutions, not the text similarity.
    # Usefulness: depends on context. For programming tasks this can be functional completeness. If the LLM's solution does the same thing as the optimal solution the score should be '1'

    # Use OpenAI function calling to generate a usefulness score
    messages=[
            {"role": "system", "content": "You are an AI that analyses submitted solutions to tasks and rates them against their optimal solutions. You give scores based on how useful the submitted solutions are compared to the optimal solution"},
            {"role": "user", "content": f"A task was given to a language model and completed. Given the task, rate the usefulness of the solution compared to the optimal solution \n\nTask:\n{tasks[task]}\n\nSubmitted solution:\n{result}\n\nOptimal solution:\n{tasks[task]['optimal_solution']}\n\nRate on a scale of 0 to 1, where 0 means no usefulness and 1 means equally useful to the optimal solution."},
    ]
    functions={
            "name": "rate",
            "description": "rates the submitted solution compared to the optimal solution",
            "parameters": {
                "type": "object",
                "properties": {
                    "explanation": {
                        "type": "string",
                        "description": "Short explanation on the given score. Think step by step. 500 characters max."
                    },
                    "score": {
                        "type": "float",
                        "description": "Score between 0 and 1. The score is a usefulness score. Depending on the context this can be anything. For code it should be practicality - does the code do exactly what the optimal solution does?"
                    },

                },
                "required": ["explanation", "score"]
            }
        }
    response = openai_chat_completion(model, messages, functions)
    # extract score from response its one of the two fields
    score = float(response) # type: ignore
    return score

def analyze_prompt_quality(task, prompt, result, optimal_result, score, model):
    # Use OpenAI function calling to analyze the quality of the prompt
    messages=[
        {"role": "system", "content": "You are an AI that analyzes the quality of prompts used to generate solutions to tasks. You identify key instructions that made the prompt good."},
        {"role": "user", "content": f"Given the task, the prompt used, the result from the prompt, the optimal result, and the score, analyze the quality of the prompt and identify what made it good. \n\nTask:\n{task}\n\nPrompt used:\n{prompt}\n\nResult from prompt:\n{result}\n\nOptimal result:\n{optimal_result}\n\nScore:\n{score}\n\nIdentify key instructions that made the prompt good."},
    ]
    analysis = openai_chat_completion(model, messages)
    return analysis

# TOOD (maybe):
# - parallel execute everything
# - provide GPT with prompts that were already generated so it stays unique
# - experiment with generating multiple prompts in one go VS one by one
# - add some kind of tag on the tasks like [code] which should have the LLM generate only code

def main():
    prompts = {}
    for task_key, task_value in tasks.items():
        prompts[task_key] = generate_prompts_for_task(task_value, model, variation_count)

    results = {}
    for task_key, prompt in prompts.items():
        results[task_key] = execute_prompts(prompts[task_key], model, task_run_count)

    # Print the results in a structured way
    for task_key, task_results in results.items():
        print(f"\nTask: {task_key}")
        for prompt_index, prompt_results in task_results.items():
            print(f"\tPrompt {prompt_index + 1}:")
            for run_index, run_result in enumerate(prompt_results):
                print(f"\t\tRun {run_index + 1}: {run_result}")


    return
    # Compare results to optimal and score them
    scored_results = {}
    for task in tasks:
        scores = []
        for result in results[task]:
            scores.append(score_task_result(task, result, tasks, model))
        # Take the average of all scores for a given prompt
        scored_results[task] = sum(scores) / len(scores) if scores else 0

    # Print the results in a user-friendly way and write them to a file
    with open('results.txt', 'w') as f:
        for task in tasks:
            score = scored_results[task]
            print(f"Task: {task}\nScore: {score}\n", file=f)

    # Analyze the quality of the prompts and save them to a file
    with open('prompt_analysis.txt', 'w') as f:
        for task in tasks:
            prompt = prompts[task]
            for result in results[task]:
                optimal_result = tasks[task]['optimal_solution']
                score = scored_results[task]
                analysis = analyze_prompt_quality(task, prompt, result, optimal_result, score, model)
                print(f"Task: {task}\nPrompt: {prompt}\nAnalysis: {analysis}\n", file=f)
    

if __name__ == "__main__":
    main()