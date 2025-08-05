# This is the code for making immediate calls

import datetime, copy, time
import openai
import anthropic


# This is a simple text query to see if the answer shows the LLM is being nonresponsive
def is_unresponsive(response:str) -> bool:
    nonresponse_tags = ["sorry", "can't assist", "cannot assist", "I apologize"]
    for tag in nonresponse_tags:
        if tag.lower() in response.lower():
            return True
    return False


def raw_call(messages_arg, model:str) -> str:
    count_exceptions = 0
    count_unresponsive = 0
    while count_unresponsive < 10:
        messages = copy.deepcopy(messages_arg)  # do deepcopy to keep any changes from interfering with calling function's copy
        rv = None
        try:
            if model.startswith("gpt-4"):
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=4095,
                    timeout=60,
                    seed=42
                )
                rv = response.choices[0].message.content

            elif model.startswith("o1"):
                # Note that o1 and o3 do not support temperatures
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    timeout=240,
                    seed=42
                )
                rv = response.choices[0].message.content

            elif model.startswith("o3-20"):
                # Note that o1 and o3 do not support temperatures
                # With o3, we always want to use high reasoning effort
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    timeout=240,
                    seed=42,
                    reasoning_effort="high"
                )

                print("ACTUAL INPUT TOKENS :", response.usage.prompt_tokens)
                print("REASONING TOKENS    :", response.usage.completion_tokens_details.reasoning_tokens)
                print("ACTUAL OUTPUT TOKENS:", response.usage.completion_tokens- \
                                                response.usage.completion_tokens_details.reasoning_tokens)

                rv = response.choices[0].message.content

            elif model.startswith("o3-pro"):
                # Note that o1 and o3 do not support temperatures
                # With o3-pro, reasoning effort at high is too expensive
                client = openai.OpenAI()
                response = client.responses.create(
                    model=model,
                    input=messages
                )

                print("INPUT TOKENS        :", response.usage.input_tokens)
                print("REASONING TOKENS    :", response.usage.output_tokens_details.reasoning_tokens)
                print("ACTUAL OUTPUT TOKENS:",
                      response.usage.output_tokens-response.usage.output_tokens_details.reasoning_tokens)

                rv = response.choices[0].message.content

            elif model.startswith("claude-3"):
                client = anthropic.Anthropic()

                response = client.messages.create(
                    model=model,
                    max_tokens=4095,
                    temperature=0,
                    messages=messages)

                rv = response.content[0].text

            elif model.startswith("claude-sonnet-4") or \
                    model.startswith("claude-opus-4-20250514"):
                client = anthropic.Anthropic(timeout=300.0)
                # Set the token budget to be the maximum (32000) for claude-opus-4-20250514
                # Then set the reasoning-token budget to be half of that (16000)
                # When setting thinking parameter, cannot also set temperature, alas
                response = client.messages.create(
                    model=model,
                    max_tokens=32000,
                    thinking={"type": "enabled", "budget_tokens": 16000},
                    messages=messages)

                assert type(response.content[0]) == anthropic.types.thinking_block.ThinkingBlock
                assert type(response.content[1]) == anthropic.types.text_block.TextBlock
                print("INPUT TOKENS  (exact):", response.usage.input_tokens)
                print("SUMMARY THINKING TOKENS (approx):", len(response.content[0].thinking.split()))
                print("OUTPUT TOKENS (exact):", response.usage.output_tokens)

                rv = response.output_text

            else:
                assert False, "Model not supported"

        except Exception as e:  # Catches most exceptions; often LLM APIs have temporary hiccups
            count_exceptions += 1
            print("EXCEPTION from ", model, f", Error Type: {type(e).__name__} {e}, try number {count_exceptions}")
            if count_exceptions >= 10:
                raise  # re-throw it, since we've tried repeatedly
            else:
                time.sleep(10) # hopefully LLM API hiccup will be resolved
        else:
            if not is_unresponsive(rv):
                return rv
            else:
                count_unresponsive += 1
                print("Retrying call due to nonresponsive response, number", count_unresponsive, rv)


# Makes call(s) to API to get Yes/No answers (along with the explanation)
# Also returns the timestamp from the log file
def call_api_yesno(prompt:str,
                    model:str,
                    context:str) -> (bool, str, str):
    count_not_yesno = 0
    while count_not_yesno < 10:
        messages = [{"role": "user", "content": prompt}]
        response1 = raw_call(messages, model)
        stripped_response = response1.strip().strip(".").lower()
        if stripped_response == "yes":
            timestamp = log_messages_freeform(messages, context)
            return True, response1, timestamp
        elif stripped_response == "no":
            timestamp = log_messages_freeform(messages, context)
            return False, response1, timestamp
        print("Making Yes/No Followup Call")
        messages.append({"role": "assistant", "content": response1}) # store to re-call and to write to log
        messages.append({"role": "user", "content": "So the answer (just Yes or No) is:"})
        response2 = raw_call(messages, model) # call again!
        messages.append({"role": "assistant", "content": response2}) # store for writing to log
        stripped_response = response2.strip().strip(".*").lower() # the * is stripped since LLMs may try to bold the answer
        if stripped_response.startswith("yes"):
            timestamp = log_messages_freeform(messages, context)
            return True, response1, timestamp
        elif stripped_response.startswith("no"):
            timestamp = log_messages_freeform(messages, context)
            return False, response1, timestamp
        count_not_yesno += 1
        print("Retrying call due to failure to get yes or no, number",
              count_not_yesno, "response instead was:", response2)
    # If we are here, there were too many nonresponsive
    print("TOO MANY NONRESPONSIVE")
    return False, response1, ""


# This allows logging messages with freeform background information
# Returns the datetime stamp used in the log, to allow cross-referencing, if needed.
def log_messages_freeform(messages, background:str):
    timestamp = str(datetime.datetime.now())
    with open("calls.LOG", "a") as logfile:
        logfile.write("*******************************************\n")
        logfile.write(timestamp + "\n")
        if background is not None and len(background.strip()) > 0:
            logfile.write(str(background) + "\n")
        for message in messages:
            logfile.write("****** " + message["role"] + "\n")
            logfile.write(message["content"])
            logfile.write("\n")
    return timestamp

# Allows writing any type of information into the log file
# Returns the datetime stamp used in the log, to allow cross-referencing, if needed.
def log_arbitrary(information:str):
    timestamp = str(datetime.datetime.now())
    with open("calls.LOG", "a") as logfile:
        logfile.write("*******************************************\n")
        logfile.write(timestamp + "\n")
        logfile.write(information + "\n")
    return timestamp
