from Chat_v1 import llm_generate_answer
import os
import json


# under this there are trace_i
# i is from 1 to 47.
# under trace_i: actions.json (a list of actions (Ground truth))
# and AXTree_before_action_k.json (k is from 1 to n) (it only has one element in the dict: "AXTree":"str")
# The AXTree is the web observation for action k  
# in the instruction set. the dictionary has one: "Instructions_offline"
# it is a list of instructione (47)

def generate_next_action_prompt(action_history: list[str], user_instruction: str, axtree: str) -> str:
    """
    Generate the full prompt for the Amazon Web Agent's next action selection.

    Args:
        action_history (list[str]): A list of past actions taken by the agent.
        user_instruction (str): The user's natural language instruction.
        axtree (str): The flattened string representation of the accessibility tree.

    Returns:
        str: The full formatted prompt string.
    """
    
    system_prompt = """You are an Amazon Web Agent, designed to complete the user instruction by interacting with Amazon websites. You must act carefully and responsibly. You should only perform actions that are aligned with completing the instruction. Avoid taking unnecessary steps or exploring unrelated parts of the page.

Review the current state of the page and all other information to find the best
possible next action to accomplish the instruction. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.

# User Instruction
"""

    action_space = """# Currently open tabs

Tab 0 (active tab)
  Title: Amazon.com. Spend less. Smile more.
  URL: https://www.amazon.com/

# Current page Accessibility Tree.
""" + axtree + """

# Action Space


11 different types of actions are available.

noop(wait_ms: float = 1000)
    Examples:
        noop()

        noop(500)

go_back()
    Examples:
        go_back()

go_forward()
    Examples:
        go_forward()

goto(url: str)
    Examples:
        goto('http://www.example.com')

fill(bid: str, value: str)
    Examples:
        fill('237', 'example value')

        fill('45', 'multi-line\\nexample')

        fill('a12', 'example with "quotes"')

select_option(bid: str, options: str | list[str])
    Examples:
        select_option('a48', 'blue')

        select_option('c48', ['red', 'green', 'blue'])

click(bid: str, button: Literal['left', 'middle', 'right'] = 'left', modifiers: list[typing.Literal['Alt', 'Control', 'ControlOrMeta', 'Meta', 'Shift']] = [])
    Examples:
        click('a51')

        click('b22', button='right')

        click('48', button='middle', modifiers=['Shift'])

hover(bid: str)
    Examples:
        hover('b8')

press(bid: str, key_comb: str)
    Examples:
        press('88', 'Backspace')

        press('a26', 'ControlOrMeta+a')

        press('a61', 'Meta+Shift+t')

clear(bid: str)
    Examples:
        clear('996')

stop(reason: str)
    Examples:
        stop('The task is finished!')

        stop('To finish this task, I need your account email and password.')

Only a single action can be provided at once. Example:
fill('a12', 'example with "quotes"')


Here are examples of actions with chain-of-thought reasoning:

I now need to click on the Submit button to send the form. I will use the click action on the button, which has bid 12.
```click("12")```

I now need to search for black shoes on Amazon. I will use the fill action on the search input, which has bid 138.
```fill("138", "black shoes")```"""

    thinking_header = "\n\n# Next action.   You will now think step by step and produce your next best action. Reflect on your past actions, any resulting error message, and the current state of the page before deciding on your next action."

    if action_history and len(action_history)>0:
        history_str = "\n# Action History\n" + "\n".join(action_history)
    else:
        history_str = "\n# Action History\nNone yet."

    prompt = (
        system_prompt
        + user_instruction
        + "\n"
        + action_space
        + history_str
        + thinking_header
    )
    
    return prompt
def generate_single_trajectory(trace_dir, trace_num, instruction: str):
    """
    Generate a list of prompts for a single trace.

    Args:
        trace_dir (str): Path to the root trace directory.
        trace_num (int): Trace index (1-based).
        instruction (str): Corresponding user instruction.

    Returns:
        list[str]: A list of prompts, one for each step.
    """
    trace_path = os.path.join(trace_dir, f"trace_{trace_num}")
    
    # Load actions
    with open(os.path.join(trace_path, "actions.json"), "r") as f:
        actions = json.load(f)

    prompts = []
    action_history = []

    # action k has AXTree_before_action_k.json, so we iterate from 1 to len(actions)
    for k in range(1, len(actions)+1):
        axtree_path = os.path.join(trace_path, f"AXTree_before_action_{k}.json")
        if not os.path.exists(axtree_path):
            print(f"Missing AXTree file: {axtree_path}")
            continue

        with open(axtree_path, "r") as f:
            axtree_json = json.load(f)
            axtree_str = axtree_json["AXTree"]

        prompt = generate_next_action_prompt(action_history, instruction, axtree_str)
        prompts.append({
            "step": k,
            "prompt": prompt,
            "ground_truth_action": actions[k-1]
        })

        action_history.append(f"```{actions[k-1]}```")  # Append ground truth action

    return prompts


def generate_trajectories(instruction_path: str, trajectory_dir: str):
    """
    Process all traces and generate prompts for each.

    Args:
        instruction_path (str): Path to the JSON file with instructions.
        trajectory_dir (str): Directory containing trace folders trace_1 to trace_47.

    Returns:
        dict: { trace_id: [ {step, prompt, ground_truth_action}, ... ] }
    """
    with open(instruction_path, "r") as f:
        instructions = json.load(f)["Instructions_offline"]

    all_traces = {}
    for i in range(1, len(instructions)+1):
        instruction = instructions[i-1]
        trace_prompts = generate_single_trajectory(trajectory_dir, i, instruction)
        all_traces[f"trace_{i}"] = trace_prompts

    return all_traces


if __name__ == "__main__":
    instruction_path = "/Users/xianrenz/Project/Xianren_upload/Shopping_agent_benchmark/offline_instructions.json"
    trajectory_dir = "/Users/xianrenz/Project/Xianren_upload/Shopping_agent_benchmark/record"
    all_prompts = generate_trajectories(instruction_path, trajectory_dir)

    # Optionally save to file for later use
    with open("all_trace_prompts.json", "w") as f:
        json.dump(all_prompts, f, indent=2)