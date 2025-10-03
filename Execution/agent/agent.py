#from Chat_v1 import llm_generate_answer
import openai
from browsergym.experiments.agent import Agent as BrowserGymAgent
from browsergym.experiments.agent import AgentInfo
from browsergym.experiments import AbstractAgentArgs, Agent
import dataclasses
from browsergym.utils.obs import flatten_axtree_to_str, flatten_dom_to_str, prune_html
from browsergym.core.action.highlevel import HighLevelActionSet
from agent.Chat import SimpleGeneration,AWSConfig,ModelConfig
import logging
import base64
from PIL import Image
import numpy as np
import io
import os

def merge_chat_messages_as_string(system_msgs: str, user_msgs: str) -> str:
    """
    Converts a system + user message into a single string as a merged prompt.
    Useful for debugging or when using non-chat completions.

    Args:
        system_msg: The content of the system message.
        user_msg: The content of the user message.

    Returns:
        A string that simulates the full prompt.
    """
    def extract_text(blocks):
        return "\n\n".join(block["text"].strip() for block in blocks if block.get("type") == "text")

    system_text = extract_text(system_msgs)
    user_text = extract_text(user_msgs)

    merged_prompt = f"System:\n{system_text}\n\nUser:\n{user_text}"
    return merged_prompt




logger = logging.getLogger(__name__)

def image_to_jpg_base64_url(image: np.ndarray | Image.Image):
    """Convert a numpy array to a base64 encoded image url."""

    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    if image.mode in ("RGBA", "LA"):
        image = image.convert("RGB")

    with io.BytesIO() as buffer:
        image.save(buffer, format="JPEG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/jpeg;base64,{image_base64}"

@dataclasses.dataclass
class MyAgentArgs(AbstractAgentArgs):
    """
    This class is meant to store the arguments that define the agent.

    By isolating them in a dataclass, this ensures serialization without storing
    internal states of the agent.
    """

    model_name: str = "Local_Claude_3_7"
    chat_mode: bool = False
    demo_mode: str = "off"
    use_html: bool = False
    use_axtree: bool = True
    use_screenshot: bool = False

    def make_agent(self):
        return Local_Agent(
            model_name=self.model_name,
            chat_mode=self.chat_mode,
            demo_mode=self.demo_mode,
            use_html=self.use_html,
            use_axtree=self.use_axtree,
            use_screenshot=self.use_screenshot,
        )

class Local_Agent(Agent):
    def obs_preprocessor(self, obs: dict) -> dict:

        return {
            "chat_messages": obs["chat_messages"],
            "screenshot": obs["screenshot"],
            "goal_object": obs["goal_object"],
            "last_action": obs["last_action"],
            "last_action_error": obs["last_action_error"],
            "open_pages_urls": obs["open_pages_urls"],
            "open_pages_titles": obs["open_pages_titles"],
            "active_page_index": obs["active_page_index"],
            "axtree_txt": flatten_axtree_to_str(obs["axtree_object"]),
            "pruned_html": None #prune_html(flatten_dom_to_str(obs["dom_object"]))
        }
    # , "html": obs["html"]
    def __init__(
        self,
        model_name: str,
        chat_mode: bool,
        demo_mode: str,
        use_html: bool,
        use_axtree: bool,
        use_screenshot: bool,
    ) -> None:
        super().__init__()
        self.model_name = model_name
        self.chat_mode = chat_mode
        self.use_html = use_html
        self.use_axtree = use_axtree
        self.use_screenshot = use_screenshot

        if not (use_html or use_axtree):
            raise ValueError(f"Either use_html or use_axtree must be set to True.")

        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set. Export it in your shell first.")
        self.openai_client = openai.OpenAI(api_key=key)
        self.action_set = HighLevelActionSet(
            subsets=["nav", "Ashop", "stop"],  # "chat",# define a subset of the action space
            # subsets=["chat", "bid", "coord", "stop"] # allow the agent to also use x,y coordinates
            strict=False,  # less strict on the parsing of the actions
            multiaction=False,  # does not enable the agent to take multiple actions at once
            demo_mode=demo_mode,  # add visual effects
        )
        # use this instead to allow the agent to directly use Python code
        # self.action_set = PythonActionSet())

        self.action_history = []
    
    def get_action(self, obs: dict) -> tuple[str, dict]:
        system_msgs = []
        user_msgs = []

        if self.chat_mode:
            system_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# Instructions

You are a UI Assistant, your goal is to help the user perform tasks using a web browser. You can
communicate with the user via a chat, to which the user gives you instructions and to which you
can send back messages. You have access to a web browser that both you and the user can see,
and with which only you can interact via specific commands. 

Review the instructions from the user, the current state of the page and all other information
to find the best possible next action to accomplish your goal. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.
""",
                }
            )
            # append chat messages
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# Chat Messages
""",
                }
            )
            for msg in obs["chat_messages"]:
                if msg["role"] in ("user", "assistant", "stop"):
                    user_msgs.append(
                        {
                            "type": "text",
                            "text": f"""\
- [{msg['role']}] {msg['message']}
""",
                        }
                    )
                elif msg["role"] == "user_image":
                    user_msgs.append({"type": "image_url", "image_url": msg["message"]})
                else:
                    raise ValueError(f"Unexpected chat message role {repr(msg['role'])}")

        else:
            assert obs["goal_object"], "The goal is missing."
            system_msgs.append(
                {
                    "type": "text",
                    "text": f"""\


You are an Amazon Web Agent, designed to complete the user instruction by interacting with Amazon websites. You must act carefully and responsibly. You should only perform actions that are aligned with completing the instruction. Avoid taking unnecessary steps or exploring unrelated parts of the page.
Do your best to fulfill the instruction. You should stop when the task is clearly complete or if more necessary information is needed from the user to proceed.

Review the current state of the page and all other information to find the best
possible next action to accomplish the instruction. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.
""",
                }
            )
            # append goal
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# User Instruction
""",
                }
            )
            # goal_object is directly presented as a list of openai-style messages
            user_msgs.extend(obs["goal_object"])

        # append url of all open tabs
        user_msgs.append(
            {
                "type": "text",
                "text": f"""\
# Currently open tabs
""",
            }
        )
        for page_index, (page_url, page_title) in enumerate(
            zip(obs["open_pages_urls"], obs["open_pages_titles"])
        ):
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
Tab {page_index}{" (active tab)" if page_index == obs["active_page_index"] else ""}
  Title: {page_title}
  URL: {page_url}
""",
                }
            )

        # append page AXTree (if asked)
        if self.use_axtree:
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# Current page Accessibility Tree

{obs["axtree_txt"]}

""",
                }
            )
        # append page HTML (if asked)
        if self.use_html:
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# Current page DOM

{obs["pruned_html"]}

""",
                }
            )

        # append page screenshot (if asked)
        if self.use_screenshot:
            user_msgs.append(
                {
                    "type": "text",
                    "text": """\
# Current page Screenshot
""",
                }
            )
            user_msgs.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_to_jpg_base64_url(obs["screenshot"]),
                        "detail": "auto",
                    },  # Literal["low", "high", "auto"] = "auto"
                }
            )

        # append action space description
        user_msgs.append(
            {
                "type": "text",
                "text": f"""\
# Action Space

{self.action_set.describe(with_long_description=False, with_examples=True)}

Here are examples of actions with chain-of-thought reasoning:

I now need to click on the Submit button to send the form. I will use the click action on the button, which has bid 12.
```click("12")```

I now need to search for black shoes on Amazon. I will use the fill action on the search input, which has bid 138.
```fill("138", "black shoes")```

""",
            }
        )

        # append past actions (and last error message) if any
        if self.action_history:
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
# History of past actions
""",
                }
            )
            user_msgs.extend(
                [
                    {
                        "type": "text",
                        "text": f"""\

{action}
""",
                    }
                    for action in self.action_history
                ]
            )

            if obs["last_action_error"]:
                user_msgs.append(
                    {
                        "type": "text",
                        "text": f"""\
# Error message from last action

{obs["last_action_error"]}

""",
                    }
                )

        # ask for the next action
        user_msgs.append(
            {
                "type": "text",
                "text": f"""\
# Next action

You will now think step by step and produce your next best action. Reflect on your past actions, any resulting error message, and the current state of the page before deciding on your next action.
""",
            }
        )

        prompt_text_strings = []
        for message in system_msgs + user_msgs:
            match message["type"]:
                case "text":
                    prompt_text_strings.append(message["text"])
                case "image_url":
                    image_url = message["image_url"]
                    if isinstance(message["image_url"], dict):
                        image_url = image_url["url"]
                    if image_url.startswith("data:image"):
                        prompt_text_strings.append(
                            "image_url: " + image_url[:30] + "... (truncated)"
                        )
                    else:
                        prompt_text_strings.append("image_url: " + image_url)
                case _:
                    raise ValueError(
                        f"Unknown message type {repr(message['type'])} in the task goal."
                    )
        full_prompt_txt = "\n".join(prompt_text_strings)
        logger.info(full_prompt_txt)

        
        # query OpenAI model
        
        response = self.openai_client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_msgs},
                {"role": "user", "content": user_msgs},
            ],
        )
        action = response.choices[0].message.content
        
        '''
        all_messages = system_msgs + user_msgs
        # Amazon bedrock
        
        all_messages = merge_chat_messages_as_string(system_msgs,user_msgs)
        action = self.openai_client._get_response_chat(all_messages) 
        '''
        
        self.action_history.append(action)

        return action, {}


