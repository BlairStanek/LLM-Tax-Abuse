import datetime, copy, argparse
import call_utils, utils, batch_utils

parser = argparse.ArgumentParser(
    description='Runs Goal Verification (with or without analysis, or with adversarial step) on Shelter Check dataset')
parser.add_argument('--standard', required=False,
                    choices=["viable", "correct"],
                    help='which standard to tell the LLM to use')
parser.add_argument('--num', required=False, type=int,
                    help='number of which strategy to run over; if not passed, then ALL are run')
parser.add_argument('--model', required=True,
                    help='which LLM to call or prepare to call')
parser.add_argument('--test', required=True,
                    choices=["goal_verification_without_analysis",
                             "goal_verification_with_analysis",
                             "goal_verification_adversarial_step"],
                    help='which test to run')
parser.add_argument('--callnow', action="store_true",
                    help='whether to make the calls right now or in batch')
args = parser.parse_args()
print("args=", args)
start_timestamp = call_utils.log_arbitrary("goal_verification, with args=" + str(args))

list_ids_prompts = [] # These will be actually passed to the LLM; list of 2-tuples of (id, prompt)
for filename in utils.get_list_filenames():
    if args.num is None or filename == utils.get_filename_from_prefix(args.num):
        include_analysis = (args.test == "goal_verification_with_analysis")
        use_adversarial_step = (args.test == "goal_verification_adversarial_step")

        authorities_str, background_str, goal_str, strategy_str, analysis_str, \
            adversarial_step_str, primary_area_str, strategy_type_str = utils.parse_file(filename)

        prompt_start = "You will be determining whether a specified tax strategy meets a particular goal, "
        if include_analysis:
            prompt_start += "given the authorities, factual background, and analysis of the strategy below. "
        else:
            prompt_start += "given the authorities and factual background below. "
        prompt_start += utils.IGNORE_DOCTRINES_PROMPT_TEXT

        prompt_start += "\n\nHere are the authorities you will be applying:\n\n" + authorities_str
        if len(background_str.strip()) > 0:
            prompt_start += "\n\nHere is the background:\n\n" + background_str

        prompt_start += "\n\nHere is the strategy:\n\n"
        if use_adversarial_step:
            prompt_start += utils.replace_adversarial_step(strategy_str, adversarial_step_str)
        else:
            prompt_start += strategy_str

        if include_analysis:
            prompt_start += "\n\nHere is an analysis of the strategy:\n\n" + analysis_str

        if include_analysis:
            prompt_start += "\n\nBased on the legal authorities, background, and analysis above, "
        else:
            prompt_start += "\n\nBased on the legal authorities and background above, "

        if args.standard == 'viable':
            prompt_start += "is it viable that the strategy above meets the following goal?  " + \
                            "Spell out your reasoning in detail, and resolve all reasonable doubts " + \
                            "in favor of the strategy being viable for meeting the goal.  Here is the goal: "
        elif args.standard == 'correct':
            prompt_start += "is it correct that the strategy above meets the following goal?  " + \
                            "Spell out your reasoning in detail.  Here is the goal: "
        else:
            assert False

        # Iterate over all goals for the strategy.  Most strategies have only one goal, but some have
        # up to four.  We want to meet all goals for a strategy to "pass."
        goals = utils.strip_numbering(goal_str)
        for idx_goal, goal in enumerate(goals):
            prompt = prompt_start + goal

            id = "Strategy_" + utils.get_prefix_from_filename(filename) + \
                "_Goal_" + str(idx_goal+1)
            list_ids_prompts.append((id, prompt))

if args.callnow:
    num_correct = 0
    total_called = 0
    for id, prompt in list_ids_prompts:
        print("********: id=", id)
        print(prompt)
        correct, explanation, timestamp = \
            call_utils.call_api_yesno(prompt, args.model, "goal_verification: " + str(args))
        print("TIMESTAMP =", timestamp)
        print("CORRECT=", correct)
        print(explanation)
        total_called += 1
        if correct:
            num_correct += 1
    print("num_correct =", num_correct, "; total_called =", total_called)
else: # then we are creating a batch file
    if args.num is None:
        testname = batch_utils.get_testname(args.test, args.model)
    else:
        testname = batch_utils.get_testname(args.test + "_" + str(args.num), args.model)
    print("testname=", testname)
    batch_filename = batch_utils.write_batch_file(testname,
                                                  batch_utils.POSTFIX_UPLOAD1,
                                                  args.model,
                                                  list_ids_prompts)
    batch_utils.upload_file_and_start(batch_filename, args.model)
