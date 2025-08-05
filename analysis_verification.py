import datetime, copy, argparse
import call_utils, utils, batch_utils

parser = argparse.ArgumentParser(
    description='Runs Analysis Verification on Shelter Check dataset')
parser.add_argument('--standard', required=False,
                    choices=["viable", "correct"],
                    help='which standard to tell the LLM to use')
parser.add_argument('--num', required=False, type=int,
                    help='number of which strategy to run over; if not passed, then ALL are run')
parser.add_argument('--model', required=True,
                    help='which LLM to call or prepare to call')
parser.add_argument('--callnow', action="store_true",
                    help='whether to make the calls right now or in batch')
args = parser.parse_args()
print("args=", args)
start_timestamp = call_utils.log_arbitrary("analysis_verification, with args=" + str(args))

list_ids_prompts = [] # These will be actually passed to the LLM; list of 2-tuples of (id, prompt)
for filename in utils.get_list_filenames():
    if args.num is None or filename == utils.get_filename_from_prefix(args.num):
        authorities_str, background_str, goal_str, strategy_str, analysis_str, \
            adversarial_step_str, primary_area_str, strategy_type_str = utils.parse_file(filename)

        analysis_steps = utils.strip_numbering(analysis_str)

        prompt_start = "You will be verifying some legal analysis "
        prompt_start += "of a tax strategy, given authorities and factual background.  "
        prompt_start += utils.IGNORE_DOCTRINES_PROMPT_TEXT
        prompt_start += "\n\nHere are the authorities you will be applying:\n\n" + authorities_str
        if len(background_str.strip()) > 0:
            prompt_start += "\n\nHere is the background:\n\n" + background_str
        prompt_start += "\n\nHere is the strategy:\n\n"
        prompt_start += strategy_str
        prompt_start += "\n\n"

        for idx_analysis, analysis_step in enumerate(analysis_steps):
            prompt = prompt_start

            if idx_analysis > 0:
                prompt += "Assume that the following analysis is " + args.standard + ":\n"
                for prev_analysis in range(idx_analysis):
                    prompt += analysis_steps[prev_analysis] + "\n"
                prompt += "\n"

            if args.standard == 'viable':
                prompt += "Even if it is not necessarily correct, is the following analysis potentially viable, " + \
                "based on the information and authorities provided? Spell out your reasoning in detail, and " + \
                "resolve all reasonable doubts in favor of the analysis being viable.  " + \
                "Here is the analysis to weigh: " + analysis_step
            elif args.standard == 'correct':
                prompt += "Is the following analysis correct, based on the information and authorities provided? " + \
                "Spell out your reasoning in detail. Here is the analysis to weigh: " + analysis_step
            else:
                assert False

            id = "Strategy_" + utils.get_prefix_from_filename(filename) + \
                "_Analysis_" + str(idx_analysis+1)
            list_ids_prompts.append((id, prompt))

if args.callnow:
    num_correct = 0
    total_called = 0
    for id, prompt in list_ids_prompts:
        print("********: id=", id)
        print(prompt)
        correct, explanation, timestamp = \
            call_utils.call_api_yesno(prompt, args.model, "analysis_verification: " + str(args))
        print("TIMESTAMP =", timestamp)
        print("CORRECT=", correct)
        print(explanation)
        total_called += 1
        if correct:
            num_correct += 1
    print("num_correct =", num_correct, "; total_called =", total_called)
else: # then we are creating a batch file
    if args.num is None:
        testname = batch_utils.get_testname("analysis_verification", args.model)
    else:
        testname = batch_utils.get_testname("analysis_verification" + "_" + str(args.num), args.model)
    print("testname=", testname)
    batch_filename = batch_utils.write_batch_file(testname,
                                                  batch_utils.POSTFIX_UPLOAD1,
                                                  args.model,
                                                  list_ids_prompts)
    batch_utils.upload_file_and_start(batch_filename, args.model)
