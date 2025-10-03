import os
import pickle
import gzip
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any
from PIL import Image
import json
from typing import List, Union

@dataclass
class AgentTrajectory:
    instruction: str
    screenshots: List[Union[Path, str]] = field(init=False)
    actions: List[str] = field(init=False)
    axtrees: List[str] = field(init=False)
    nova: bool = field(init=False)

    def __init__(self,
                 instruction: str,
                 screenshots: List[Union[Path, str]],
                 actions: List[str],
                 axtrees: List[str] = None,
                 nova: bool = False):
        self.instruction = instruction
        self.screenshots = screenshots
        self.actions = actions
        self.nova = nova
        self.axtrees = axtrees if axtrees is not None else []

        # Enforce type consistency
        if nova:
            if not all(isinstance(s, str) for s in screenshots):
                raise ValueError("When nova=True, screenshots must be base64 strings (List[str])")
        else:
            if not all(isinstance(s, Path) for s in screenshots):
                raise ValueError("When nova=False, screenshots must be file paths (List[Path])")



def load_step_info(path: Path):
    try:
        with gzip.open(path, 'rb') if path.suffix == '.gz' else open(path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"Failed to load {path.name}: {e}")
        return None


def collect_agent_trajectories(base_dir: Path) -> Dict[str, AgentTrajectory]:
    trajectories = {}
    for folder in sorted(base_dir.iterdir()):
        if not folder.is_dir():
            continue

        step_files = sorted(folder.glob("step_*.pkl*"))
        if not step_files:
            continue

        screenshots = []
        actions = []
        axtrees = []
        instruction = None

        for step_file in step_files:
            step = load_step_info(step_file)
            if step is None:
                continue

            if instruction is None and step.obs and "chat_messages" in step.obs:
                messages = step.obs["chat_messages"]
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        instruction = msg.get("message")
                        break

            # collect action
            actions.append(step.action)

            # collect screenshot path
            screenshot_path = folder / f"screenshot_step_{step.step}.png"
            if screenshot_path.exists():
                screenshots.append(screenshot_path)

            # collect axtree
            axtree_path = folder / f"axtree_step_{step.step}.txt"
            if axtree_path.exists():
                try:
                    axtree = axtree_path.read_text()
                    axtrees.append(axtree)
                except Exception as e:
                    print(f"Failed to read {axtree_path.name}: {e}")
                    axtrees.append("")

        if instruction:
            trajectories[instruction] = AgentTrajectory(
                instruction=instruction,
                screenshots=screenshots,
                actions=actions,
                axtrees=axtrees
            )

    return trajectories


def collect_agent_trajectories_voyager(base_dir: Path) -> Dict[str, AgentTrajectory]:
    # Load ID → instruction mapping
    task_path = Path("/Users/xianrenz/Project/voyager/WebVoyager/data/tasks_test.jsonl")
    id_to_instruction = {}
    with open(task_path, 'r') as f:
        for line in f:
            item = json.loads(line)
            id_to_instruction[item['id']] = item['ques']

    trajectories = {}
    for task_dir in sorted(base_dir.iterdir()):
        if not task_dir.is_dir() or not task_dir.name.startswith("task"):
            continue

        task_id = task_dir.name.replace("task", "")
        instruction = id_to_instruction.get(task_id)
        if instruction is None:
            continue

        # Collect screenshots
        screenshots = sorted(
            [f for f in task_dir.glob("screenshot*.png") if f.is_file()],
            key=lambda p: int(p.stem.replace("screenshot", ""))
        )

        # Collect actions from interact_messages.json
        interact_path = task_dir / "interact_messages.json"
        if not interact_path.exists():
            continue

        with open(interact_path, "r") as f:
            messages = json.load(f)
        actions = [
            m["content"].split("Action:")[-1].strip()
            for m in messages
            if m["role"] == "assistant" and "Action:" in m["content"]
        ]

        # We don't have axtree files here
        axtrees = []

        try:
            trajectories[instruction] = AgentTrajectory(
                instruction=instruction,
                screenshots=screenshots,
                actions=actions,
                axtrees=axtrees,
                nova=False
            )
        except Exception as e:
            print(f"[Error] task{task_id}: {e}")

    return trajectories


def collect_agent_trajectories_nova(base_dir: Path) -> Dict[str, AgentTrajectory]:
    trajectories = {}

    for trace_dir in sorted(base_dir.glob("trace_*")):
        if not trace_dir.is_dir():
            continue

        # Look for a single act_*.json file inside the subdirectory
        act_json_files = list(trace_dir.glob("*/act_*.json"))
        if not act_json_files:
            continue

        act_path = act_json_files[0]
        with open(act_path) as f:
            steps = json.load(f)

        if not steps:
            continue

        screenshots = []
        actions = []
        axtrees = []  # Not used in nova

        instruction = steps[0]['request']['kwargs']['task'].split(", format output with jsonschema:")[0]

        for step in steps:
            # Get action
            raw_action = step['response'].get('rawProgramBody', '').strip()
            actions.append(raw_action)

            # Directly use the base64-encoded image string
            screenshot_base64 = step['request'].get('screenshot', '')
            if screenshot_base64.startswith("data:image"):
                screenshots.append(screenshot_base64)
            else:
                print("Warning: screenshot missing or not base64 encoded")

        # Create trajectory (nova=True will enforce the screenshot type in __init__)
        trajectories[instruction] = AgentTrajectory(
            instruction=instruction,
            screenshots=screenshots,
            actions=actions,
            axtrees=axtrees,
            nova=True
        )

    return trajectories

