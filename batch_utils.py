# This file handles batch processing of requests to the various APIs
import openai
import anthropic
from google.cloud import storage # batch processing by VertexAI requires loading to/from Google Cloud
from google.oauth2 import service_account
from google import genai
from google.genai.types import CreateBatchJobConfig, JobState, HttpOptions
from google.cloud import aiplatform_v1 # used to actually access the output directory
import datetime, json, call_utils, os
from dotenv import load_dotenv

load_dotenv(dotenv_path="sheltercheck.env", override=True)

DIR_BATCH_UPLOADS = "Batch_Uploads/"
DIR_BATCH_DOWNLOADS = "Batch_Downloads/"
POSTFIX_UPLOAD1 = "_upload1"
POSTFIX_UPLOAD2 = "_upload2"
POSTFIX_DOWNLOAD1 = "_download1"
POSTFIX_DOWNLOAD2 = "_download2"

GOOGLE_PROJECT  = "sheltercheck"
GOOGLE_LOCATION = os.getenv("GOOGLE_LOCATION")
GOOGLE_BUCKET   = os.getenv("GOOGLE_BUCKET")
GOOGLE_OUTPUT_PREFIX = "batch‑out/"       # GCS folder for results

def get_testname(test:str, model:str) -> str:
    assert " " not in test and ":" not in test and ";" not in test, "Prohibited for files"
    return test + "_" + model + "_" + str(datetime.datetime.now().strftime("%Y-%m-%dat%H.%M.%S"))

def is_openai(model:str) -> bool:
    return model.startswith("gpt-") or model.startswith("o3")

def is_claude(model:str) -> bool:
    return model.startswith("claude-sonnet-4") or \
        model.startswith("claude-opus-4") or \
        model.startswith("claude-3")

def is_google(model:str) -> bool:
    return model.startswith("gemini")

def write_batch_file(testname:str, postfix:str, model:str, list_ids_prompts:list):
    assert " " not in testname and ":" not in testname and ";" not in testname, "Prohibited for files"
    assert len([x[0] for x in list_ids_prompts]) == len(set([x[0] for x in list_ids_prompts])), "need unique ids!"
    filename = DIR_BATCH_UPLOADS + testname + postfix + ".jsonl"

    with open(filename, "w", encoding="utf‑8") as f:
        for i, id_prompt in enumerate(list_ids_prompts):
            assert len(id_prompt) in [2, 4] # only supported sizes
            if len(id_prompt) == 2:
                if is_openai(model) or is_claude(model):
                    messages = [ {"role": "user", "content": id_prompt[1]}]
                elif is_google(model):
                    messages = [{"role": "user",
                                 "parts": [{"text": id_prompt[1]}]
                                 }]

            elif len(id_prompt) == 4:
                if is_openai(model) or is_claude(model):
                    messages = [
                        {"role": "user", "content": id_prompt[1]},
                        {"role": "assistant", "content": id_prompt[2]},
                        {"role": "user", "content": id_prompt[3]}
                    ]
                elif is_google(model):
                    messages = [
                        {"role": "user", "parts": [{"text": id_prompt[1]}]},
                        {"role": "model", "parts": [{"text": id_prompt[2]}]},
                        {"role": "user", "parts": [{"text": id_prompt[3]}]}
                    ]
            else:
                assert False, "Size not supported"

            if is_openai(model):
                request_line = {
                    "custom_id": id_prompt[0],  # must be unique
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": model,
                        "messages": messages,
                        "reasoning_effort": "high"
                    }
                }
            elif is_claude(model):
                request_line = {
                    "custom_id": id_prompt[0],     # unique per request
                    "params": {
                        "model": model,
                        "max_tokens": 16000,
                        "thinking": {"type": "enabled", "budget_tokens": 8000},
                        "messages": messages
                    }
                }
            elif is_google(model):
                request_line = \
                    {"key": id_prompt[0],
                        "request": {
                            "contents": messages
                        }
                     }

            json.dump(request_line, f)
            f.write("\n")
    return filename

def upload_file_and_start(filename:str, model:str):
    infotext = "Uploaded file " + filename + " against model" + model + "\n"

    if is_openai(model):
        client = openai.OpenAI()
        file_id = client.files.create(
            file=open(filename, "rb"),
            purpose="batch"
        ).id
        infotext += "now fileid=" +  file_id + "\n"
        batch = client.batches.create(
            input_file_id=file_id,
            endpoint="/v1/chat/completions",
            completion_window="24h"  # only option today; delivers within 24 h
        )
        print("batch.id=", batch.id)
        infotext += "batch.id:" + batch.id + "\n"

    elif is_claude(model):
        client = anthropic.Anthropic()
        requests = []
        with open(filename, "r") as f:
            for line in f.readlines():
                requests.append(json.loads(line))

        batch = client.messages.batches.create(requests=requests)
        print("Batch ID:", batch.id)
        infotext += "batch.id:" + batch.id + "\n"

    elif is_google(model):
        # authenticate to Google Cloud Storage
        # creds = service_account.Credentials.from_service_account_file("sheltercheck-googlecloudkey.json", \
        #                                                               scopes=[
        #                                                                   "https://www.googleapis.com/auth/cloud-platform"])

        # upload to google cloud storage
        gs_filename = filename[len(DIR_BATCH_UPLOADS):]
        storage_client = storage.Client(project=GOOGLE_PROJECT) #, credentials=creds)
        bucket = storage_client.bucket(GOOGLE_BUCKET)
        blob = bucket.blob("gemini_input/" + gs_filename)
        blob.upload_from_filename(filename)

        # make actual call
        client = genai.Client(http_options=HttpOptions(api_version="v1"),
                              vertexai=True, project=GOOGLE_PROJECT, location=GOOGLE_LOCATION)
        assert filename.startswith(DIR_BATCH_UPLOADS)
        SRC_URI = f"gs://{GOOGLE_BUCKET}/gemini_input/{gs_filename}"  # ← already uploaded
        DEST_URI = f"gs://{GOOGLE_BUCKET}/gemini_output/"  # ← empty folder for results

        job = client.batches.create(
            model=model,
            src=SRC_URI,
            config=CreateBatchJobConfig(dest=DEST_URI),
        )
        print(f"JOB NAME = {job.name} (state={job.state})")
        infotext += "job.name:" + job.name + "\n"
    else:
        assert False, "not supported"

    # Do logging
    with open(filename, "r") as f:
        infotext += f.read()
    call_utils.log_arbitrary(infotext)


def download_response(batchid:str, outfile_name:str, model:str):
    log_text = "DOWNLOADED " + outfile_name + " from model=" + model + " w/batchid=" + batchid + "\n"

    if is_openai(model):
        client = openai.OpenAI()
        batch = client.batches.retrieve(batchid)
        output_file_id = batch.output_file_id
        print("output file id:", output_file_id)
        client.files.content(output_file_id).write_to_file(outfile_name)

    elif is_claude(model):
        client = anthropic.Anthropic()
        results = client.messages.batches.results(batchid)
        outfile_text = ""
        for line in results:  # ND‑JSON stream
            assert line.result.type == "succeeded"
            outfile_text += json.dumps(line.model_dump()) +"\n"
        with open(outfile_name, "w") as f:
            f.write(outfile_text)

    elif is_google(model):
        # creds = service_account.Credentials.from_service_account_file("sheltercheck-googlecloudkey.json", \
        #                                                               scopes=[
        #                                                                   "https://www.googleapis.com/auth/cloud-platform"])

        job_service = aiplatform_v1.JobServiceClient(
            client_options={"api_endpoint": f"{GOOGLE_LOCATION}-aiplatform.googleapis.com"}
        )
        bp = job_service.get_batch_prediction_job(name=batchid)
        true_dir = bp.output_info.gcs_output_directory
        print("Predictions are under:", true_dir)

        # download from google cloud storage
        storage_client = storage.Client(project=GOOGLE_PROJECT)  # , credentials=creds)
        bucket = storage_client.bucket(GOOGLE_BUCKET)
        file_loc = true_dir + "/predictions.jsonl"
        assert file_loc.startswith("gs://")
        file_loc = file_loc[len("gs://"):]
        assert file_loc.startswith(GOOGLE_BUCKET)
        file_loc = file_loc[len(GOOGLE_BUCKET)+1:]
        blob = bucket.blob(file_loc)
        blob.download_to_filename(outfile_name)

    else:
        assert False, "not supported"

    with open(outfile_name, "r") as f:
        log_text += f.read() + "\n"
    call_utils.log_arbitrary(log_text)


def merge_input_response(input_data, response_data, model, follow_up:str):
    total_input_tokens = 0
    total_reasoning_tokens = 0
    total_output_tokens = 0
    list_ids_prompt1_response_prompt2 = []
    for response_datum in response_data:
        # count up the token usage
        if is_openai(model):
            # count tokens
            assert response_datum["error"] == None
            total_input_tokens += response_datum["response"]["body"]["usage"]["prompt_tokens"]
            total_reasoning_tokens += response_datum["response"]["body"]["usage"]["completion_tokens_details"][
                "reasoning_tokens"]
            total_output_tokens += response_datum["response"]["body"]["usage"]["completion_tokens"]

            # get the original prompt
            id = response_datum["custom_id"]
            prompt1 = None
            for input_datum in input_data:
                if input_datum["custom_id"] == id:
                    assert prompt1 == None, "Should be only one with custom_id=" + id
                    assert len(input_datum["body"]["messages"]) == 1
                    assert input_datum["body"]["messages"][0]["role"] == "user"
                    prompt1 = input_datum["body"]["messages"][0]["content"]

            # now get the response data and merge it
            assert len(response_datum["response"]["body"]["choices"]) == 1
            assert response_datum["response"]["body"]["choices"][0]["message"]["role"] == "assistant"
            response = response_datum["response"]["body"]["choices"][0]["message"]["content"]
            list_ids_prompt1_response_prompt2.append((id, prompt1, response, follow_up))


        elif is_claude(model):
            assert response_datum["result"]["type"] == "succeeded"

            total_input_tokens += response_datum["result"]["message"]["usage"]["input_tokens"]
            total_output_tokens += response_datum["result"]["message"]["usage"]["output_tokens"]

            # get the original prompt
            id = response_datum["custom_id"]
            prompt1 = None
            for input_datum in input_data:
                if input_datum["custom_id"] == id:
                    assert prompt1 == None, "Should be only one with custom_id=" + id
                    assert len(input_datum["params"]["messages"]) == 1
                    assert input_datum["params"]["messages"][0]["role"] == "user"
                    prompt1 = input_datum["params"]["messages"][0]["content"]

            # now get the response data and merge it
            response = None
            for content in response_datum["result"]["message"]["content"]:
                if content["type"] == "text": # other type includes "thinking"
                    assert response == None
                    response = content["text"]
            list_ids_prompt1_response_prompt2.append((id, prompt1, response, follow_up))

        elif is_google(model):
            input_data, response_data, model, follow_up

            total_input_tokens += response_datum["response"]["usageMetadata"]["promptTokenCount"]
            total_output_tokens += response_datum["response"]["usageMetadata"]["candidatesTokenCount"]

            id = response_datum["key"]
            prompt1 = response_datum["request"]["contents"][0]["parts"][0]["text"]
            assert len(response_datum["request"]["contents"]) == 1
            assert len(response_datum["request"]["contents"][0]["parts"]) == 1
            assert response_datum["request"]["contents"][0]["role"] == "user"

            assert len(response_datum["response"]["candidates"]) == 1
            assert len(response_datum["response"]["candidates"][0]["content"]["parts"]) == 1
            assert response_datum["response"]["candidates"][0]["content"]["role"] == "model"
            assert response_datum["response"]["candidates"][0]["finishReason"] == "STOP"
            response = response_datum["response"]["candidates"][0]["content"]["parts"][0]["text"]
            list_ids_prompt1_response_prompt2.append((id, prompt1, response, follow_up))


        else:
            assert False, "model not implemented"

    # Here is useful information for keeping track of costs
    return list_ids_prompt1_response_prompt2, total_input_tokens, total_reasoning_tokens, total_output_tokens

def extract_response(downloaded_filename:str, model:str):
    download_data = []
    with open(downloaded_filename, "r") as f:
        for line in f.readlines():
            download_data.append(json.loads(line))

    total_input_tokens = 0
    total_reasoning_tokens = 0
    total_output_tokens = 0
    list_ids_responses = []

    for response_datum in download_data:
        if is_openai(model):
            assert response_datum["error"] == None
            total_input_tokens += response_datum["response"]["body"]["usage"]["prompt_tokens"]
            total_reasoning_tokens += response_datum["response"]["body"]["usage"]["completion_tokens_details"][
                "reasoning_tokens"]
            total_output_tokens += response_datum["response"]["body"]["usage"]["completion_tokens"]
            id = response_datum["custom_id"]
            assert len(response_datum["response"]["body"]["choices"]) == 1
            assert response_datum["response"]["body"]["choices"][0]["message"]["role"] == "assistant"
            response = response_datum["response"]["body"]["choices"][0]["message"]["content"]
        elif is_claude(model):
            assert response_datum["result"]["type"] == "succeeded"
            total_input_tokens += response_datum["result"]["message"]["usage"]["input_tokens"]
            total_output_tokens += response_datum["result"]["message"]["usage"]["output_tokens"]
            id = response_datum["custom_id"]

            response = None
            for content in response_datum["result"]["message"]["content"]:
                if content["type"] == "text":  # other type includes "thinking"
                    assert response == None, "should be only one"
                    response = content["text"]
        elif is_google(model):
            id = response_datum["key"]

            assert len(response_datum["response"]["candidates"]) == 1
            assert response_datum["response"]["candidates"][0]["finishReason"] == "STOP"

            total_input_tokens += response_datum["response"]["usageMetadata"]["promptTokenCount"]
            total_output_tokens += response_datum["response"]["usageMetadata"]["candidatesTokenCount"]

            assert len(response_datum["response"]["candidates"][0]["content"]["parts"]) == 1
            response = response_datum["response"]["candidates"][0]["content"]["parts"][0]["text"]
        else:
            assert False, "not implemented"
        list_ids_responses.append((id, response))

    return list_ids_responses, total_input_tokens, total_reasoning_tokens, total_output_tokens

