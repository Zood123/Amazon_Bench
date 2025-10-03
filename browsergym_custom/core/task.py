from abc import ABC, abstractmethod
from typing import Tuple

import numpy as np
import playwright.sync_api

EMAIL = "xianrenz+0-175323319372195JR@amazon.com"
PASSWORD = "lmhrj7qmf4r5p%20"

class AbstractBrowserTask(ABC):
    """
    Abstract class for browsergym tasks.

    """

    @classmethod
    def get_task_id(cls):
        raise NotImplementedError

    def __init__(self, seed: int) -> None:
        # initiate a random number generator
        self.random = np.random.RandomState(seed)

        # task properties, will be used to set up the browsergym environment
        # default values, can be overriden in children classes
        self.viewport = {"width": 1280, "height": 720}
        self.slow_mo = 1000  # ms
        self.timeout = 5000  # ms
        self.locale = None  # see https://playwright.dev/python/docs/api/class-browser#browser-new-context-option-locale
        self.timezone_id = None  # see https://playwright.dev/python/docs/api/class-browser#browser-new-context-option-timezone-id

    @abstractmethod
    def setup(self, page: playwright.sync_api.Page) -> tuple[str, dict]:
        """
        Set up everything needed to execute the task.

        Args:
            page: the active playwright page.

        Returns:
            goal: str, goal of the task.
            info: dict, custom information from the task.
        """

    @abstractmethod
    def validate(
        self, page: playwright.sync_api.Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        """
        Validate the task was completed successfully

        Args:
            page: the active playwright page.
            chat_messages: the chat messages.

        Returns:
            reward: float, the reward obtained since last call to validate().
            done: boolean flag, indicates if the task has finished or not (be it success or fail).
            message: string, a new user message for the chat.
            info: dictionnary, custom information from the task.

        """

    def cheat(self, page: playwright.sync_api.Page, chat_messages: list[str]) -> None:
        """
        Solve the task using a pre-defined solution (optional).

        """
        raise NotImplementedError

    def teardown(self) -> None:
        """
        Tear down the task and clean up any resource / data created by the task (optional).

        """
        pass


class OpenEndedTask(AbstractBrowserTask):
    @classmethod
    def get_task_id(cls):
        return "openended"

    def __init__(self, seed: int, start_url: str, goal: str = None) -> None:
        """
        Args:
            seed: random seed.
            start_url: str, the url for the starting page.
            goal: str, the initial goal.

        """
        super().__init__(seed)
        self.start_url = start_url
        self.goal = goal

    def setup(self, page: playwright.sync_api.Page) -> tuple[str, dict]:
        page.goto(self.start_url, timeout=20000)
        return self.goal, {}

    def teardown(self) -> None:
        pass

    def validate(
        self, page: playwright.sync_api.Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        reward, done, msg, info = 0, False, "", {}

        for message in chat_messages:
            if message["role"] == "user" and message["message"] == "exit":
                done = True
                break

        return reward, done, msg, info





class ExploreTask(AbstractBrowserTask):
    """A lightweight variant of *openended* with a single upfront goal.

    The task starts at a given URL and shows the **instruction once**. There is
    no ongoing conversation—`validate()` just waits for the agent to send the
    special user message "exit" (or to time out, depending on the runner).
    """

    # ---------------------------------------------------------------------
    # Static helpers
    # ---------------------------------------------------------------------
    @classmethod
    def get_task_id(cls):
        return "explore"

    # ---------------------------------------------------------------------
    # Life‑cycle methods required by AbstractBrowserTask
    # ---------------------------------------------------------------------
    def __init__(self, seed: int, start_url: str ="https:www.amazon.com", goal: str=None) -> None:
        super().__init__(seed)
        
        self.start_url = start_url
        self.goal = goal

        

    # ------------------------------------------------------------------
    def setup(self, page: playwright.sync_api.Page) -> Tuple[str, dict]:
        """Navigate to *start_url* and return the single instruction."""
        page.goto(self.start_url, timeout=40000)

        try:
            page.wait_for_selector("#nav-link-accountList", timeout=10000)
            # Step 2: Click "Sign in"
            page.click("#nav-link-accountList")
            #page.click("text=Sign in")
        except:
            print("try amazon account page")
            page.goto("https://www.amazon.com/a/addresses")
            
        # Fill email and continue
        page.wait_for_selector('input[name="email"]')
        page.fill('input[name="email"]', EMAIL, timeout=10000)
        page.press('input[name="email"]', 'Enter')

        page.wait_for_timeout(1000)
        # Wait for password input (may fail if CAPTCHA or MFA is triggered)
        page.wait_for_selector('input[name="password"]', timeout=10000)
        page.fill('input[name="password"]', PASSWORD)
        page.click('input#signInSubmit')
        
        # Optional: wait for navigation or check login status
        page.wait_for_load_state('domcontentloaded')
        page.goto("https://www.amazon.com/")

        return self.goal, {}

    # ------------------------------------------------------------------
    def validate(
        self, page: playwright.sync_api.Page, chat_messages: list[dict]
    ) -> Tuple[float, bool, str, dict]:
        """No incremental rewards; episode ends when user says ``exit``."""
        #done = any(m["role"] == "user" and m["message"].strip().lower() == "exit" for m in chat_messages)
        return 0.0, False, "", {}

    # ------------------------------------------------------------------
    def cheat(self, page: playwright.sync_api.Page, chat_messages: list[dict]):
        """Optional shortcut to end the task for debugging; not implemented."""
        pass

    # ------------------------------------------------------------------
    def teardown(self):
        pass
