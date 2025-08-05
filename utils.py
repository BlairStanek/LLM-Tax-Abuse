import os

IGNORE_DOCTRINES_PROMPT_TEXT = "Do **NOT** consider the " + \
        "application of any tax-law judicial doctrines like substance-over-form, " + \
        "the sham-transaction doctrine, or economic substance."

FREEFORM_DIR = "FreeformOutputsGraded"

def strip_numbering(in_str:str):
    lines = [line.strip() for line in in_str.split("\n") if len(line.strip()) > 0]
    for i in range(len(lines)):
        assert lines[i].startswith(str(i+1)+") ") # ensure the line numbering is correct
        lines[i] = lines[i][len(str(i+1)+") "):] # strip the line numbering
    return lines

# Given the prefix, find the filename
def get_filename_from_prefix(prefix:str):
    for filename in os.listdir("Strategies"):
        if filename.startswith(str(prefix) + "_") and filename.endswith(".txt"):
            return filename
    return None

# Given the filename, find the prefix
def get_prefix_from_filename(filename:str):
    assert "_" in filename
    return filename.split("_")[0]

# Gets a list of the filenames, sorted by index (i.e., 1_ first, then 2_, ... )
def get_list_filenames():
    rv = []
    prefix = 1
    while True:
        filename = get_filename_from_prefix(str(prefix))
        if filename is None:
            return rv
        else:
            rv.append(filename)
        prefix += 1


def replace_adversarial_step(strategy_str:str, adversarial_step_str:str) -> str:
    assert "\n" not in adversarial_step_str.strip(), "Current code assumes a single false step; may extend later"
    strategy_lines = strip_numbering(strategy_str)
    assert len(strategy_lines) >= 2, "expected at least two steps in real strategy"

    adversarial_step_num = -1
    assert adversarial_step_str[0].isnumeric()
    if adversarial_step_str[1].isnumeric(): # handle steps 10 thru 99
        adversarial_step_num = int(adversarial_step_str[0:2])
    else:
        adversarial_step_num = int(adversarial_step_str[0])
    assert 1 <= adversarial_step_num <= len(strategy_lines), "False strategy step should be to replace one of the existing ones"

    # If first step
    if adversarial_step_num == 1:
        idx_two = strategy_str.find("\n2)")
        return adversarial_step_str.strip() + strategy_str[idx_two:]
    # If last step
    elif adversarial_step_num == len(strategy_lines):
        idx_last = strategy_str.find("\n" + str(adversarial_step_num) + ")")
        return strategy_str[0:idx_last+1] + adversarial_step_str.strip()
    # If in between first and last
    else:
        idx_start = strategy_str.find("\n" + str(adversarial_step_num) + ")")
        idx_end = strategy_str.find("\n" + str(adversarial_step_num+1) + ")")
        return strategy_str[0:idx_start + 1] + adversarial_step_str.strip() + strategy_str[idx_end:]

# We open the file and get the relevant portions of it out
def parse_file(filename):
    in_str = open("Strategies/" + filename, "r").read()
    first_authority_idx = in_str.find("\nAUTHORITY")
    assert first_authority_idx > 0, "expected AUTHORITY"
    background_idx = in_str.find("\nBACKGROUND:")
    assert background_idx > 0, "expected BACKGROUND"
    goal_idx = in_str.find("\nGOALS:")
    assert goal_idx > 0, "expected GOALS"
    strategy_idx = in_str.find("\nSTRATEGY:")
    assert strategy_idx > 0, "expected STRATEGY"
    analysis_header = "\nANALYSIS (the analysis numbering below does NOT correspond to the strategy step numbering above):"
    analysis_idx = in_str.find(analysis_header)
    assert analysis_idx > 0, "expected ANALYSIS"
    adversarial_step_header = "\nADVERSARIAL STRATEGY STEP(S):"
    adversarial_step_idx = in_str.find(adversarial_step_header)
    assert adversarial_step_idx > 0, "expected FALSE STRATEGY STEP(S)"
    primary_area_idx = in_str.find("\nPRIMARY TAX-LAW AREA:")
    assert primary_area_idx > 0, "expected PRIMARY TAX-LAW AREA"
    strategy_type_idx = in_str.find("\nSTRATEGY TYPE:")
    assert strategy_type_idx > 0, "expected STRATEGY TYPE"
    notes_idx = in_str.find("\nNOTES:")
    assert first_authority_idx < background_idx < goal_idx < strategy_idx \
           < analysis_idx < adversarial_step_idx < primary_area_idx < strategy_type_idx < notes_idx
    authorities_str = in_str[first_authority_idx:background_idx].strip()
    background_str = in_str[background_idx+len("\nBACKGROUND:"):goal_idx].strip()
    goal_str = in_str[goal_idx+len("\nGOALS:"):strategy_idx].strip()
    strategy_str = in_str[strategy_idx+len("\nSTRATEGY:"):analysis_idx].strip()
    analysis_str = in_str[analysis_idx+len(analysis_header):adversarial_step_idx].strip()
    adversarial_step_str = in_str[adversarial_step_idx+len(adversarial_step_header):primary_area_idx].strip()
    primary_area_str = in_str[primary_area_idx+len("\nPRIMARY TAX-LAW AREA:"):strategy_type_idx].strip()
    assert primary_area_str in ["Income Tax", "Partnership", "International",
                                "Corporate", "Employee Benefits"]
    strategy_type_str = in_str[strategy_type_idx+len("\nSTRATEGY TYPE:"):notes_idx].strip()
    # These strategies are the three set out by Joseph E. Stiglitz, “The General Theory of Tax Avoidance,”
    # 38 National Tax J. 325-337 (Sept. 1985), plus a fourth "Legal Cleverness" that Stiglitz, as a
    # non-lawyer did not appreciate and discuss.
    assert strategy_type_str in ["Arbitrage Between Taxpayers", "Arbitrage Between Rates",
                                 "Deferral", "Legal Cleverness"]

    return authorities_str, background_str, goal_str, strategy_str, analysis_str, \
        adversarial_step_str, primary_area_str, strategy_type_str

# This returns the number of strategy steps for a particular file
def count_strategy_steps(filename):
    _, _, _, strategy_str, _, _, _, _ = parse_file(filename)
    strategy_lines = strip_numbering(strategy_str)
    return len(strategy_lines)

# Used for step-cloze across batches
def get_strategy_step_by_str(strategy_step_str:str) -> str:
    segs = strategy_step_str.split("_")
    assert len(segs) == 4, "Expected something like Strategy_2_Step_6"
    assert segs[0] == "Strategy"
    assert segs[2] == "Step"
    strategy_num = int(segs[1])
    step_num = int(segs[3])
    strategy_file = get_filename_from_prefix(str(strategy_num))
    _, _, _, strategy_str, _, _, _, _ = parse_file(strategy_file)
    lines = [line.strip() for line in strategy_str.split("\n") if len(line.strip()) > 0]
    filtered_lines = [line for line in lines if line.startswith(str(step_num)+")")]
    assert len(filtered_lines) == 1
    return filtered_lines[0][len(str(step_num))+1:].strip()


# Used for step-cloze across batches
def make_strategy_step_str(strategy_num, step_num) -> str:
    return "Strategy_" + str(strategy_num) + \
            "_Step_" + str(step_num)


# Running this file directly goes through and tabulates the area and strategy counts
# for the dataset.
if __name__ == "__main__":
    count_files = 0
    DIR = "./Strategies"
    strategy_counts = dict()
    primary_area_counts = dict()
    background_steps = []
    goal_steps = []
    analysis_steps = []
    strategy_steps = []
    filenames = get_list_filenames()
    total_num_steps = 0
    print("{:<44} ".format("FILENAME"), "num strategy steps")

    for filename in filenames:
        assert os.path.isfile(DIR + "/" + filename)
        assert filename.lower().endswith(".txt")

        count_files += 1
        _, background_str, goal_str, strategy_str, analysis_str, \
           adversarial_step_str, primary_area_str, strategy_type_str = parse_file(filename)

        primary_area_counts[primary_area_str] = 1 + primary_area_counts.get(primary_area_str, 0)
        strategy_counts[strategy_type_str] = 1 + strategy_counts.get(strategy_type_str, 0)

        num_strategy_steps = count_strategy_steps(filename)

        print("{:<44} ".format(filename[:-4]), num_strategy_steps)
        total_num_steps += num_strategy_steps

        strategy_steps.append(num_strategy_steps)
        background_steps.append(len(strip_numbering(background_str)))
        goal_steps.append(len(strip_numbering(goal_str)))
        analysis_steps.append(len(strip_numbering(analysis_str)))

    print("Total steps:", total_num_steps)

    print("Primary Area:")
    for k, v in primary_area_counts.items():
        print(k, "\t", v)
    print("***")
    print("Strategy Type:")
    for k, v in strategy_counts.items():
        print(k, "\t", v)

    print("strategy_steps:", min(strategy_steps), max(strategy_steps), sum(strategy_steps)/36.0)
    print("background_steps:", min(background_steps), max(background_steps), sum(background_steps)/36.0)
    print("goal_steps:", min(goal_steps), max(goal_steps), sum(goal_steps)/36.0)
    print("analysis_steps:", min(analysis_steps), max(analysis_steps), sum(analysis_steps)/36.0)
