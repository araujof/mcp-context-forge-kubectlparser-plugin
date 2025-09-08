"""A KubeCtl command parser and pre-processor.

Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Fred Araujo

This module loads configurations for plugins.
"""

from typing import Any

# First-Party
from mcpgateway.plugins.framework import (
    Plugin,
    PluginConfig,
    PluginContext,
    ToolPreInvokePayload,
    ToolPreInvokeResult,
)

from kubectlcmdprocessor.parser import KubectlParser

CONTEXT_KEY_POLICY_CONTEXT = "opa_policy_context"
CONTEXT_KEY_KUBECTL_CMD = "kubectlcmd"


class KubectlCmdProcessor(Plugin):
    """A KubeCtl command parser and pre-processor."""

    def __init__(self, config: PluginConfig):
        """Entry init block for plugin.

        Args:
          logger: logger that the skill can make use of
          config: the skill configuration
        """
        super().__init__(config)

    async def tool_pre_invoke(self, payload: ToolPreInvokePayload, context: PluginContext) -> ToolPreInvokeResult:
        """Plugin hook run before a tool is invoked.

        Args:
            payload: The tool payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the tool can proceed.
        """
        if not payload.args:
            return ToolPreInvokeResult(continue_processing=True)
        await self.process_args_in_state(payload.args, context)
        return ToolPreInvokeResult(continue_processing=True)

    async def process_args_in_state(self, args: dict[str, Any], context: PluginContext) -> None:
        """Process arguments and store them in process context state."""
        if len(args) > 1:
            raise ValueError(f"Plugin: {self.name} only works on single argument functions.")
        for arg in args.values():
            parser = KubectlParser()
            context.global_context.state[CONTEXT_KEY_POLICY_CONTEXT] = {CONTEXT_KEY_KUBECTL_CMD: parser.parse(str(arg))}
