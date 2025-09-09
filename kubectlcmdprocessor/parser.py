"""A KubeCtl command parser and pre-processor.

Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: Fred Araujo

This module parses kubectl commands into an intermediate representation.
"""

from typing import Dict, List, Any


class KubectlParser:
    """Parser for kubectl CLI commands"""

    # Common kubectl verbs
    VERBS = {
        "get",
        "describe",
        "create",
        "apply",
        "delete",
        "edit",
        "patch",
        "replace",
        "expose",
        "run",
        "set",
        "explain",
        "logs",
        "attach",
        "exec",
        "port-forward",
        "proxy",
        "cp",
        "auth",
        "scale",
        "autoscale",
        "rollout",
        "label",
        "annotate",
        "completion",
        "top",
        "drain",
        "cordon",
        "uncordon",
        "cluster-info",
        "config",
        "plugin",
        "version",
        "api-resources",
        "api-versions",
        "certificate",
        "wait",
        "debug",
        "taint",
    }

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset parser state"""
        self.command = {"verb": None, "resource": None, "namespace": None, "args": [], "flags": []}

    def parse(self, command_string: str) -> Dict[str, Any]:
        """
        Parse a kubectl command string into structured format

        Args:
            command_string: The kubectl command as a string

        Returns:
            Dictionary with parsed command structure
        """
        self.reset()

        # Remove 'kubectl' from the beginning if present
        command_string = command_string.strip()
        if command_string.startswith("kubectl"):
            command_string = command_string[7:].strip()

        if not command_string:
            return {"command": self.command}

        # Split the command into tokens, respecting quoted strings
        tokens = self._tokenize(command_string)

        if not tokens:
            return {"command": self.command}

        # Parse the tokens
        self._parse_tokens(tokens)

        return {"command": self.command}

    def _tokenize(self, command_string: str) -> List[str]:
        """
        Tokenize the command string, respecting quoted arguments
        """
        # Use shlex-like parsing to handle quotes properly
        tokens = []
        current_token = ""
        in_quotes = False
        quote_char = None
        i = 0

        while i < len(command_string):
            char = command_string[i]

            if not in_quotes:
                if char in ['"', "'"]:
                    in_quotes = True
                    quote_char = char
                elif char.isspace():
                    if current_token:
                        tokens.append(current_token)
                        current_token = ""
                else:
                    current_token += char
            else:
                if char == quote_char:
                    in_quotes = False
                    quote_char = None
                else:
                    current_token += char

            i += 1

        if current_token:
            tokens.append(current_token)

        return tokens

    def _parse_tokens(self, tokens: List[str]) -> None:
        """
        Parse the tokenized command
        """
        i = 0

        # Find the verb (first non-flag token)
        while i < len(tokens) and tokens[i].startswith("-"):
            flag_consumed = self._parse_flag(tokens[i], tokens, i)
            i += flag_consumed

        if i < len(tokens):
            potential_verb = tokens[i]
            if potential_verb in self.VERBS:
                self.command["verb"] = potential_verb
                i += 1

        # Define verbs that take arguments directly (no resource type)
        DIRECT_ARG_VERBS = {"logs", "exec", "attach", "port-forward", "cp", "debug", "apply"}

        # Parse remaining tokens
        while i < len(tokens):
            token = tokens[i]

            if token.startswith("-"):
                # Handle flags
                flag_consumed = self._parse_flag(token, tokens, i)
                i += flag_consumed
            else:
                # Handle arguments based on verb type
                if self.command["verb"] in DIRECT_ARG_VERBS:
                    # For these verbs, all non-flag arguments go to args
                    self.command["args"].append(token)
                else:
                    # Standard verb resource [name] pattern
                    if self.command["resource"] is None:
                        self.command["resource"] = token
                    else:
                        self.command["args"].append(token)
                i += 1

    def _parse_flag(self, flag: str, tokens: List[str], index: int) -> int:
        """
        Parse a flag and its potential value

        Returns:
            Number of tokens consumed (1 for flag only, 2 for flag + value)
        """
        # Handle combined short flags (e.g., -it -> -i, -t)
        if flag.startswith("-") and not flag.startswith("--") and len(flag) > 2 and flag[2] != "=":
            # Split combined flags like -it into individual flags
            for char in flag[1:]:  # Skip the initial dash
                individual_flag = "-" + char
                self._parse_single_flag(individual_flag, tokens, index)
            return 1

        return self._parse_single_flag(flag, tokens, index)

    def _parse_single_flag(self, flag: str, tokens: List[str], index: int) -> int:
        """
        Parse a single flag and its potential value

        Returns:
            Number of tokens consumed (1 for flag only, 2+ for flag + value(s))
        """
        # Handle namespace flag specially
        if flag in ["-n", "--namespace"]:
            if index + 1 < len(tokens) and not tokens[index + 1].startswith("-"):
                self.command["namespace"] = tokens[index + 1]
                self.command["flags"].append({"name": flag, "value": tokens[index + 1]})
                return 2
            else:
                self.command["flags"].append({"name": flag, "value": None})
                return 1

        # Handle flag=value format
        if "=" in flag:
            name, value = flag.split("=", 1)
            if name == "--namespace":
                self.command["namespace"] = value

            # For selector flags, check if we need to continue parsing after the =
            if name in ["-l", "--selector"]:
                # Start with the value after =, then continue parsing additional tokens
                selector_tokens = [value]
                i = index + 1
                paren_depth = value.count("(") - value.count(")")

                while i < len(tokens):
                    token = tokens[i]

                    # Stop if we hit another flag (unless we're inside parentheses)
                    if token.startswith("-") and paren_depth == 0:
                        break

                    selector_tokens.append(token)

                    # Track parentheses depth
                    paren_depth += token.count("(") - token.count(")")

                    i += 1

                    # After adding this token, decide if we should continue
                    if paren_depth == 0 and selector_tokens:
                        # If we have balanced parentheses, check if we should continue
                        if i < len(tokens):
                            next_token = tokens[i]
                            # Stop if next token is a flag
                            if next_token.startswith("-"):
                                break
                            # Continue if next token is a known selector operator or continuation
                            selector_operators = {"and", "or", "!=", "==", "=", "in", "notin", ","}
                            # Check if the next token contains selector operators or is parenthetical
                            is_operator = next_token.lower() in selector_operators or any(op in next_token for op in ["=", "!", "<", ">", ","]) or next_token.startswith("(")

                            # If the current token has parentheses or next token is an operator, continue
                            # Otherwise stop - we've likely collected the complete selector
                            if not is_operator:
                                # Special case: if last token was 'in' or 'notin', continue to get the value list
                                last_token = selector_tokens[-1].lower() if len(selector_tokens) > 0 else ""
                                if last_token not in ["in", "notin"]:
                                    break

                # Join the tokens with spaces to form the complete selector expression
                selector_value = " ".join(selector_tokens)
                self.command["flags"].append({"name": name, "value": selector_value})
                return 1 + len(selector_tokens) - 1  # flag + additional tokens (value after = is already included)
            else:
                self.command["flags"].append({"name": name, "value": value})
                return 1

        # Handle selector flags that may have complex expressions
        if flag in ["-l", "--selector"]:
            return self._parse_selector_flag(flag, tokens, index)

        # Check if next token is a value for this flag
        if index + 1 < len(tokens) and not tokens[index + 1].startswith("-"):
            # Common flags that take values
            value_flags = {
                "-o",
                "--output",
                "-w",
                "--watch",
                "--sort-by",
                "--field-selector",
                "--kubeconfig",
                "--context",
                "--cluster",
                "--user",
                "--certificate-authority",
                "--client-certificate",
                "--client-key",
                "--token",
                "--as",
                "--as-group",
                "--cache-dir",
                "--match-server-version",
                "--request-timeout",
                "--server",
                "-s",
                "-c",
                "-p",
                "-f",
                "-k",
                "--patch",
            }

            if flag in value_flags:
                value = tokens[index + 1]
                self.command["flags"].append({"name": flag, "value": value})
                return 2

        # Flag without value
        self.command["flags"].append({"name": flag, "value": None})
        return 1

    def _parse_selector_flag(self, flag: str, tokens: List[str], index: int) -> int:
        """
        Parse selector flags (-l, --selector) that may have complex expressions
        like 'service in (email,checkout)' without quotes

        Returns:
            Number of tokens consumed
        """
        if index + 1 >= len(tokens):
            self.command["flags"].append({"name": flag, "value": None})
            return 1

        # Start collecting selector tokens
        selector_tokens = []
        i = index + 1
        paren_depth = 0

        while i < len(tokens):
            token = tokens[i]

            # Stop if we hit another flag (unless we're inside parentheses)
            if token.startswith("-") and paren_depth == 0:
                break

            selector_tokens.append(token)

            # Track parentheses depth
            paren_depth += token.count("(") - token.count(")")

            i += 1

            # After adding this token, decide if we should continue
            if paren_depth == 0 and selector_tokens:
                # If we have balanced parentheses, check if we should continue
                if i < len(tokens):
                    next_token = tokens[i]
                    # Stop if next token is a flag
                    if next_token.startswith("-"):
                        break
                    # Continue if next token is a known selector operator or continuation
                    selector_operators = {"and", "or", "!=", "==", "=", "in", "notin", ","}
                    # Check if the next token contains selector operators or is parenthetical
                    is_operator = next_token.lower() in selector_operators or any(op in next_token for op in ["=", "!", "<", ">", ","]) or next_token.startswith("(")

                    # If the current token has parentheses or next token is an operator, continue
                    # Otherwise stop - we've likely collected the complete selector
                    if not is_operator:
                        # Special case: if last token was 'in' or 'notin', continue to get the value list
                        last_token = selector_tokens[-1].lower() if selector_tokens else ""
                        if last_token not in ["in", "notin"]:
                            break

        if selector_tokens:
            # Join the tokens with spaces to form the complete selector expression
            selector_value = " ".join(selector_tokens)
            self.command["flags"].append({"name": flag, "value": selector_value})
            return 1 + len(selector_tokens)  # flag + all selector tokens
        else:
            self.command["flags"].append({"name": flag, "value": None})
            return 1


def main():
    """Example usage of the kubectl parser"""
    parser = KubectlParser()

    # Comprehensive test cases covering all major kubectl command patterns
    test_commands = [
        # Basic resource operations
        "kubectl get pods",
        "kubectl get pods -n sre-sandbox",
        "kubectl describe pod my-pod --namespace=production",
        "kubectl delete pods --all -n test",
        # File-based operations
        "kubectl apply -f deployment.yaml",
        "kubectl create -f ./pod.json",
        "kubectl delete -f manifest.yaml",
        # Complex operations with multiple flags
        "kubectl logs my-pod -c container-name --follow --tail=100",
        "kubectl get services -o yaml --sort-by=.metadata.name",
        "kubectl exec -it my-pod -- /bin/bash",
        'kubectl create secret generic my-secret --from-literal=key="value with spaces"',
        # Subcommands
        "kubectl rollout status deployment/nginx",
        "kubectl rollout undo deployment/abc --to-revision=3",
        "kubectl config view",
        "kubectl config use-context production",
        "kubectl auth can-i create pods",
        # Creation commands with various flags
        "kubectl create deployment nginx --image=nginx --replicas=3",
        "kubectl create service clusterip my-service --tcp=80:8080",
        "kubectl create configmap my-config --from-file=config.properties",
        # Debugging and troubleshooting
        "kubectl debug my-pod --image=busybox --target=app",
        "kubectl port-forward pod/my-pod 8080:80",
        "kubectl cp /local/path pod/my-pod:/remote/path",
        "kubectl top nodes --sort-by=cpu",
        # Advanced operations
        'kubectl patch deployment nginx -p \'{"spec":{"replicas":5}}\'',
        "kubectl scale deployment nginx --replicas=10",
        "kubectl autoscale deployment nginx --min=2 --max=10 --cpu-percent=80",
        "kubectl wait --for=condition=Ready pod/my-pod --timeout=300s",
        # Cluster management
        "kubectl drain node-1 --ignore-daemonsets",
        "kubectl cordon node-1",
        "kubectl taint nodes node-1 key=value:NoSchedule",
        # Without kubectl prefix
        "get pods -o wide --all-namespaces",
        "apply -k ./kustomize-dir",
        # Edge cases
        "kubectl",  # Empty command
        "kubectl --help",  # Only flags
        "kubectl get",  # Missing resource
        # Multi-commands
        "get pods -o wide --all-namespaces && kubectl cordon node-1",
        "get pods -o wide --all-namespaces && rm -rf /tmp",
        # Combined flags
        "kubectl exec -it omi-2246081285-8u1e0 bash -c omi -n opsbridge1",
        "kubectl exec -i -t omi-2246081285-8u1e0 bash -c omi -n opsbridge1",
        "kubectl exec -ti omi-2246081285-8u1e0 bash -c omi -n opsbridge1",
        'kubectl patch deployment ad -n otel-demo --type=\'json\' -p=\'[{"op": "add", "path": "/spec/template/spec/containers/0/env/-", "value": {"name": "GRPC_RETRY_CONFIG", "value": "<your-grpc-retry-config>"}}]\'',
        # Logs
        "kubectl logs checkout-6548d7f8cb-8455c -n otel-demo",
        # Selectors
        "kubectl get deployments -n otel-demo -o jsonpath='...' --selector=service in (ad,cart,payment)",
        "kubectl get pods -n otel-demo -l service in (email,checkout)",
        "kubectl get services  --all-namespaces --field-selector metadata.namespace!=default",
        # Other corners cases
        "kubectl logs -n <namespace> $(kubectl get pods -n <namespace> --selector=app=frontend -o jsonpath='{.items[0].metadata.name}')",
        'kubectl edit deployment checkout -n otel-demo --patch \'{"spec":{"template":{"spec":{"containers":[{"name":"checkout","image":"quay.io/it-bench/supported-checkout-service-arm64:0.0.3"}]}}}}\'',
    ]

    for cmd in test_commands:
        print(f"\nCommand: {cmd}")
        result = parser.parse(cmd)
        print(f"Parsed: {result}")
        print("-" * 60)


if __name__ == "__main__":
    main()
