# This is the first file for step cloze.  This generates the actual prompt that will
# elicit the result that is the central part of the task.
import argparse, copy
import call_utils, utils, batch_utils

parser = argparse.ArgumentParser(
    description='Starts the step-cloze task on Shelter Check dataset')
parser.add_argument('--num', required=False, type=int,
                    help='number of which strategy to run over; if not passed, then ALL are run')
parser.add_argument('--model', required=True,
                    help='which LLM to call or prepare to call')
parser.add_argument('--N_shot', default=0, type=int,
                    help='number of N-shots (0, 1, or 2)')
args = parser.parse_args()
print("args=", args)
call_utils.log_arbitrary("step_cloze, with args=" + str(args))
assert args.N_shot in [0, 1, 2]

FILES_TO_EXCLUDE = [1, 11] # cannot run tests on files with steps used in N-shot
assert args.num not in FILES_TO_EXCLUDE, "this file used for N-shot"
if args.N_shot == 0:
    N_shot_examples = []
elif args.N_shot == 1:
    N_shot_examples = [("1_Distressed_Assets_Trust.txt", 3)]
elif args.N_shot == 2:
    N_shot_examples = [("1_Distressed_Assets_Trust.txt", 3), ("11_Subsidiary_Handling_Stock_Compensation.txt", 4)]


# TODO: Get the N-shots if necessary


list_ids_prompts = [] # These will be actually passed to the LLM; list of 2-tuples of (id, prompt)

# Loop over all filenames (that are not excluded or pre-specified)
for filename in utils.get_list_filenames():
    if (args.num is None or filename == utils.get_filename_from_prefix(args.num)) and \
            int(utils.get_prefix_from_filename(filename)) not in FILES_TO_EXCLUDE:
        num_strategy_steps = utils.count_strategy_steps(filename)

        # Loop over all strategy steps in that filename's strategy
        for step_num in range(1, num_strategy_steps+1):
            files_and_nums = copy.deepcopy(N_shot_examples)
            files_and_nums.append((filename , step_num))  # The final one to pass is the actual one we want completed

            user_prompt = "You will be filling in one missing step in a tax strategy that must meet a " + \
                          "specified goal or goal(s). You will be given background facts, " + \
                          "particular tax-law authorities that the strategy should employ, " + \
                          "and other steps in a tax strategy that does meet the goal or goal(s). " + \
                          utils.IGNORE_DOCTRINES_PROMPT_TEXT + "\n\n"

            # Further construct the prompt, including any N-shot examples prior to the one at hand.
            gold_standard_answer = None
            for idx_strategy_step in range(args.N_shot + 1):  # when it equals N_shot, we will be using the actual one to test
                DIVIDER = "-----------------------------------\n"
                if args.N_shot > 1 and 0 == idx_strategy_step:
                    user_prompt += "First, here are " + str(args.N_shot) + " examples of the task being completed:\n" + \
                                   DIVIDER
                elif args.N_shot > 1 and 0 < idx_strategy_step < args.N_shot:
                    user_prompt += DIVIDER + "Here is another example of the task being completed:\n" + DIVIDER
                elif args.N_shot == 1 and 0 == idx_strategy_step:
                    user_prompt += DIVIDER + "First, here is an example of the task being completed:\n" + DIVIDER
                elif args.N_shot > 0 and args.N_shot == idx_strategy_step:
                    user_prompt += DIVIDER + "Now, here is the actual task for you:\n" + DIVIDER

                cur_file, cur_step_num = files_and_nums[idx_strategy_step]
                authorities_str, background_str, goal_str, strategy_str, analysis_str, \
                    adversarial_step_str, primary_area_str, strategy_type_str = utils.parse_file(cur_file)

                goals = utils.strip_numbering(goal_str)
                is_are = "is"
                goal_goals = "goal"
                if len(goals) > 1:
                    is_are = "are"
                    goal_goals = "goals"

                strategy_steps = strategy_str.strip().split("\n")
                assert len(strategy_steps) == len(utils.strip_numbering(strategy_str))
                assert len(strategy_steps) > 1
                if len(strategy_steps) == 2:
                    step_steps = "step"
                else:
                    step_steps = "steps"

                user_prompt += "Here are the authorities to employ:\n\n" + authorities_str
                assert len(
                    background_str.strip()) > 0, "Expected background; generation makes no sense without background facts"
                user_prompt += "\n\nHere are the background facts:\n\n" + background_str.strip()
                user_prompt += "\n\nHere " + is_are + " the " + goal_goals + \
                               " the tax strategy must meet:\n\n" + goal_str
                user_prompt += "\n\nHere is a tax strategy that meets the " + goal_goals + ":\n\n"

                blanked_out_step = None
                for step in range(1, len(strategy_steps) + 1):  # 1-indexed, whereas strategy_steps is 0-indexed
                    assert strategy_steps[step - 1].startswith(str(step))
                    if step == cur_step_num:
                        user_prompt += str(step) + ") [BLANK]\n"
                        blanked_out_step = strategy_steps[step - 1][len(str(step) + ")"):].strip()
                        if idx_strategy_step == args.N_shot:
                            gold_standard_answer = blanked_out_step
                    else:
                        user_prompt += strategy_steps[step - 1] + "\n"

                user_prompt += "\nCome up with a strategy step that would replace [BLANK] and would meet the " + \
                      goal_goals + ", given the authorities, background facts, and other " + step_steps + ".  " + \
                      "Your answer must be a **single** sentence and cannot include your reasoning or " + \
                      "any legal analysis."

                if idx_strategy_step < args.N_shot:  # for N-shot items, give the answer
                    user_prompt += "\nANSWER: " + blanked_out_step + "\n\n"

            id = utils.make_strategy_step_str(utils.get_prefix_from_filename(filename), step_num)
            assert gold_standard_answer == utils.get_strategy_step_by_str(id)

            list_ids_prompts.append((id, user_prompt))


if args.num is None:
    testname = batch_utils.get_testname("step_cloze_N" + str(args.N_shot), args.model)
else:
    testname = batch_utils.get_testname("step_cloze_s" + str(args.num) + "_N" + str(args.N_shot), args.model)
print("testname=", testname)
print("NUM ITEMS=", len(list_ids_prompts))
batch_filename = batch_utils.write_batch_file(testname,
                                              batch_utils.POSTFIX_UPLOAD1,
                                              args.model,
                                              list_ids_prompts)
batch_utils.upload_file_and_start(batch_filename, args.model)
