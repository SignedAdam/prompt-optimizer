# Prompt optimizer

This project uses the OpenAI API to dynamically generate prompts for a set of tasks. The prompts are then executed (multiple times), and the results are evaluated against the optimal solutions. Then an analysis is made to identify what made the generated prompts good or bad for further improvement.

*Inspired by [@Arskuza](https://twitter.com/arskuza/status/1700150087811276850)*

## How it works

0. user provides tasks + optimal solutions
1. LLM generates X (default 5) variations of a prompt to complete a given task (user provided)
2. LLM executes each and every prompt x times (default 10) and returns generated solutions
3. LLM scores each generated solution (from step 2) in relation to optimal result (user provided in step 0). The scoring is done based on usefulness/feature completeness
4. LLM tries to extract what made the best prompts work so well

each LLM call is not linked to previous ones

---

## Prerequisites

- Python 3
- OpenAI API key (`cp .envexample .env` then open .env and set your OpenAI key)

You can install these packages using pip:

>pip install -r requirements.txt
