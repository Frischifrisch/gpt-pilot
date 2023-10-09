import platform
import uuid

from const.code_execution import MAX_COMMAND_DEBUG_TRIES, MAX_RECUSION_LAYER
from const.function_calls import DEBUG_STEPS_BREAKDOWN
from helpers.exceptions.TokenLimitError import TokenLimitError
from helpers.exceptions.TooDeepRecursionError import TooDeepRecursionError


class Debugger:
    def __init__(self, agent):
        self.agent = agent
        self.recursion_layer = 0

    def debug(self, convo, command=None, user_input=None, issue_description=None, is_root_task=False):
        """
        Debug a conversation.

        Args:
            convo (AgentConvo): The conversation object.
            command (dict, optional): The command to debug. Default is None.
            user_input (str, optional): User input for debugging. Default is None.
            issue_description (str, optional): Description of the issue to debug. Default is None.

        Returns:
            bool: True if debugging was successful, False otherwise.
        """

        self.recursion_layer += 1
        if self.recursion_layer > MAX_RECUSION_LAYER:
            self.recursion_layer = 0
            raise TooDeepRecursionError()

        function_uuid = str(uuid.uuid4())
        convo.save_branch(function_uuid)
        success = False

        for _ in range(MAX_COMMAND_DEBUG_TRIES):
            if success:
                break

            convo.load_branch(function_uuid)

            debugging_plan = convo.send_message('dev_ops/debug.prompt',
                {
                    'command': command['command'] if command is not None else None,
                    'user_input': user_input,
                    'issue_description': issue_description,
                    'os': platform.system()
                },
                DEBUG_STEPS_BREAKDOWN)

            try:
                # TODO refactor to nicely get the developer agent
                response = self.agent.project.developer.execute_task(
                    convo,
                    debugging_plan,
                    command,
                    test_after_code_changes=True,
                    continue_development=False,
                    is_root_task=is_root_task)
                success = response['success']
            except TokenLimitError as e:
                if self.recursion_layer > 0:
                    self.recursion_layer -= 1
                    raise e
        self.recursion_layer -= 1
        return response
