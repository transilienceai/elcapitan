"""Exact-scope AWS CloudFormation execution for S3 bucket versioning."""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .action_plane import (
    ActionStep,
    DeploymentCheckpoint,
    ExecutionContext,
    HealthObservation,
    ProbeResult,
)
from .hashing import canonical_json, sha256_bytes, sha256_file
from .intake import numeric_id
from .paths import PathEscape, safe_resolve


class AwsActionError(RuntimeError):
    pass


_S3_ARN = re.compile(r"^arn:(?:aws|aws-us-gov|aws-cn):s3:::(?P<bucket>[^/]+)$")
_ROLE_ARN = re.compile(
    r"^arn:(?:aws|aws-us-gov|aws-cn):iam::(?P<account>[0-9]{12}):role/.+$")
_STABLE_STACK_STATES = frozenset({
    "CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE",
})
_EXECUTOR_ENV = {
    "ELCAP_EXECUTOR_AWS_ACCESS_KEY_ID": "AWS_ACCESS_KEY_ID",
    "ELCAP_EXECUTOR_AWS_SECRET_ACCESS_KEY": "AWS_SECRET_ACCESS_KEY",
    "ELCAP_EXECUTOR_AWS_SESSION_TOKEN": "AWS_SESSION_TOKEN",
}


@dataclass(frozen=True)
class AwsCommandResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""


class AwsCommandRunner(Protocol):
    def run(self, argv: tuple[str, ...], *, timeout_seconds: float | None = None
            ) -> AwsCommandResult: ...


def aws_executor_environment(host_env: Mapping[str, str]) -> dict[str, str]:
    missing = sorted(name for name in _EXECUTOR_ENV if not host_env.get(name))
    if missing:
        raise ValueError(
            "AWS executor credentials are incomplete: " + ", ".join(missing))
    environment = {
        target: host_env[source] for source, target in _EXECUTOR_ENV.items()
    }
    if host_env.get("PATH"):
        environment["PATH"] = host_env["PATH"]
    environment["AWS_EC2_METADATA_DISABLED"] = "true"
    environment["AWS_SHARED_CREDENTIALS_FILE"] = os.devnull
    environment["AWS_CONFIG_FILE"] = os.devnull
    environment["AWS_PAGER"] = ""
    return environment


class SubprocessAwsCommandRunner:
    """Run bounded AWS CLI calls with only the dedicated executor session."""

    def __init__(self, *,
                 host_env: Mapping[str, str] | Callable[[], Mapping[str, str]],
                 executable: str = "aws",
                 timeout_seconds: float = 180) -> None:
        if not executable or timeout_seconds <= 0:
            raise ValueError("AWS CLI executable and positive timeout are required")
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self._host_env = host_env

    @property
    def environment(self) -> dict[str, str]:
        host_env = self._host_env() if callable(self._host_env) else self._host_env
        return aws_executor_environment(host_env)

    @staticmethod
    def _bounded(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        return value[:1_000_000]

    def run(self, argv: tuple[str, ...], *, timeout_seconds: float | None = None
            ) -> AwsCommandResult:
        timeout = timeout_seconds or self.timeout_seconds
        try:
            completed = subprocess.run(
                (self.executable, *argv), capture_output=True, text=True,
                check=False, timeout=timeout, env=self.environment)
        except subprocess.TimeoutExpired as exc:
            return AwsCommandResult(
                124, self._bounded(exc.stdout), self._bounded(exc.stderr)
                + f"\nAWS CLI timed out after {timeout}s")
        except OSError as exc:
            return AwsCommandResult(127, stderr=str(exc))
        return AwsCommandResult(
            completed.returncode, self._bounded(completed.stdout),
            self._bounded(completed.stderr))


@dataclass(frozen=True)
class AwsS3CloudFormationIdentity:
    resource_uid: str
    bucket_name: str
    account_id: str
    region: str
    stack_name: str
    logical_resource_id: str
    executor_role_arn: str
    cloudformation_service_role_arn: str | None


class AwsS3CloudFormationClient:
    """Read and update one stack and one bucket through a pinned executor."""

    def __init__(self, resource_uid: str, *, account_id: str, region: str,
                 stack_name: str, logical_resource_id: str,
                 executor_role_arn: str,
                 cloudformation_service_role_arn: str | None,
                 runner: AwsCommandRunner) -> None:
        match = _S3_ARN.fullmatch(resource_uid)
        if not match:
            raise ValueError("AWS execution target must be a bucket-level S3 ARN")
        role = _ROLE_ARN.fullmatch(executor_role_arn)
        if not role or role.group("account") != account_id:
            raise ValueError("AWS executor role must belong to the target account")
        if cloudformation_service_role_arn is not None:
            service_role = _ROLE_ARN.fullmatch(cloudformation_service_role_arn)
            if not service_role or service_role.group("account") != account_id:
                raise ValueError(
                    "CloudFormation service role must belong to the target account")
        if not re.fullmatch(r"[0-9]{12}", account_id):
            raise ValueError("AWS target account must be a 12-digit account id")
        if not region or not stack_name or not logical_resource_id:
            raise ValueError("AWS execution requires region, stack, and logical resource")
        self.identity = AwsS3CloudFormationIdentity(
            resource_uid, match.group("bucket"), account_id, region, stack_name,
            logical_resource_id, executor_role_arn,
            cloudformation_service_role_arn)
        self.runner = runner

    def _run_json(self, argv: tuple[str, ...], *, operation: str,
                  empty: bool = False, timeout_seconds: float | None = None):
        result = self.runner.run(argv, timeout_seconds=timeout_seconds)
        if result.exit_code != 0:
            detail = (result.stderr or result.stdout).strip()
            raise AwsActionError(
                f"AWS CLI could not {operation} (exit {result.exit_code}): "
                f"{detail or 'no diagnostic output'}")
        text = result.stdout.strip()
        if not text and empty:
            return {}
        try:
            return json.loads(text)
        except (json.JSONDecodeError, RecursionError) as exc:
            raise AwsActionError(
                f"AWS CLI returned invalid JSON while trying to {operation}: {exc}") from exc

    def assert_identity(self) -> str:
        document = self._run_json(
            ("sts", "get-caller-identity", "--output", "json"),
            operation="resolve the executor identity")
        if not isinstance(document, Mapping) or document.get("Account") != \
                self.identity.account_id:
            raise AwsActionError("AWS executor identity is outside the pinned account")
        arn = document.get("Arn")
        if not isinstance(arn, str) or not arn:
            raise AwsActionError("AWS executor identity response has no ARN")
        role_name = self.identity.executor_role_arn.rsplit("/", 1)[-1]
        expected = (
            f"arn:aws:sts::{self.identity.account_id}:assumed-role/{role_name}/")
        if not arn.startswith(expected):
            raise AwsActionError("AWS executor is not the pinned short-lived role")
        return arn

    def stack(self) -> dict:
        document = self._run_json((
            "cloudformation", "describe-stacks", "--stack-name",
            self.identity.stack_name, "--region", self.identity.region,
            "--output", "json"), operation="read the CloudFormation stack")
        stacks = document.get("Stacks") if isinstance(document, Mapping) else None
        if not isinstance(stacks, list) or len(stacks) != 1:
            raise AwsActionError("CloudFormation did not return exactly one pinned stack")
        stack = stacks[0]
        if not isinstance(stack, Mapping):
            raise AwsActionError("CloudFormation stack response is malformed")
        stack_id = stack.get("StackId")
        if (not isinstance(stack_id, str)
                or f":{self.identity.account_id}:stack/{self.identity.stack_name}/" not in stack_id):
            raise AwsActionError("CloudFormation stack identity does not match the pinned target")
        if stack.get("RoleARN") != self.identity.cloudformation_service_role_arn:
            raise AwsActionError(
                "CloudFormation stack service role differs from the approved baseline")
        return dict(stack)

    def template(self) -> dict:
        document = self._run_json((
            "cloudformation", "get-template", "--stack-name",
            self.identity.stack_name, "--template-stage", "Processed",
            "--region", self.identity.region, "--output", "json"),
            operation="read the deployed CloudFormation template")
        template = document.get("TemplateBody") if isinstance(document, Mapping) else None
        if not isinstance(template, Mapping):
            raise AwsActionError("CloudFormation response has no template object")
        resource = (template.get("Resources") or {}).get(
            self.identity.logical_resource_id)
        if not isinstance(resource, Mapping) or resource.get("Type") != "AWS::S3::Bucket":
            raise AwsActionError("pinned CloudFormation resource is not an S3 bucket")
        properties = resource.get("Properties")
        if (not isinstance(properties, Mapping)
                or properties.get("BucketName") != self.identity.bucket_name):
            raise AwsActionError("CloudFormation template does not own the pinned bucket")
        return dict(template)

    def versioning(self) -> str:
        document = self._run_json((
            "s3api", "get-bucket-versioning", "--bucket",
            self.identity.bucket_name, "--expected-bucket-owner",
            self.identity.account_id, "--region", self.identity.region,
            "--output", "json"), operation="read S3 bucket versioning", empty=True)
        if not isinstance(document, Mapping):
            raise AwsActionError("S3 versioning response is malformed")
        status = document.get("Status")
        if status is None:
            return "Disabled"
        if status not in {"Enabled", "Suspended"}:
            raise AwsActionError(f"S3 returned an unsupported versioning state {status!r}")
        return str(status)

    def update(self, template: Path, *, token: str) -> None:
        if not template.is_file() or template.stat().st_size > 51_200:
            raise AwsActionError(
                "approved CloudFormation template is missing or exceeds 51,200 bytes")
        document = self._run_json((
            "cloudformation", "update-stack", "--stack-name",
            self.identity.stack_name, "--template-body", f"file://{template}",
            "--capabilities", "CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND",
            "--client-request-token", token, "--region", self.identity.region,
            "--output", "json"), operation="start the approved CloudFormation update")
        stack_id = document.get("StackId") if isinstance(document, Mapping) else None
        if not isinstance(stack_id, str) or self.identity.account_id not in stack_id:
            raise AwsActionError("CloudFormation update did not return the pinned stack")

    def wait_for_update(self) -> None:
        result = self.runner.run((
            "cloudformation", "wait", "stack-update-complete", "--stack-name",
            self.identity.stack_name, "--region", self.identity.region),
            timeout_seconds=900)
        if result.exit_code != 0:
            detail = (result.stderr or result.stdout).strip()
            raise AwsActionError(
                "CloudFormation update did not complete successfully: "
                + (detail or f"exit {result.exit_code}"))


def _template_sha256(document: Mapping) -> str:
    return sha256_bytes(canonical_json(document))


class AwsS3VersioningCloudFormationDriver:
    def __init__(self, client: AwsS3CloudFormationClient, *,
                 id_factory=numeric_id, sleeper=time.sleep,
                 propagation_wait_seconds: int = 900) -> None:
        if propagation_wait_seconds < 900:
            raise ValueError("S3 first-enable propagation wait must be at least 900 seconds")
        self.client = client
        self.id_factory = id_factory
        self.sleeper = sleeper
        self.propagation_wait_seconds = propagation_wait_seconds

    @property
    def name(self) -> str:
        return "aws-s3-versioning-cloudformation-driver"

    def _artifacts(self, context: ExecutionContext) -> tuple[Mapping, Path, Path]:
        link = context.link.body.get("link")
        deployment = context.plan.body.get("deployment")
        if not isinstance(link, Mapping) or not isinstance(deployment, Mapping):
            raise AwsActionError("approved records have no structured AWS deployment")
        identity = self.client.identity
        expected = {
            "resource_uid": identity.resource_uid,
            "iac_engine": "aws_cdk_cloudformation",
            "stack_name": identity.stack_name,
            "logical_resource_id": identity.logical_resource_id,
            "account_id": identity.account_id,
            "region": identity.region,
            "executor_role_arn": identity.executor_role_arn,
            "cloudformation_service_role_arn": (
                identity.cloudformation_service_role_arn),
        }
        mismatched = [key for key, value in expected.items() if link.get(key) != value]
        if mismatched:
            raise AwsActionError(
                "approved IaC link does not match the pinned AWS target: "
                + ", ".join(mismatched))
        if context.plan.body.get("status") != "verified":
            raise AwsActionError("AWS execution requires a verified remediation plan")
        if deployment.get("approved_change") != (
                f"Resources.{identity.logical_resource_id}.Properties."
                "VersioningConfiguration.Status"):
            raise AwsActionError("approved plan does not contain the exact versioning change")
        if (deployment.get("executor_role_arn") != identity.executor_role_arn
                or deployment.get("cloudformation_service_role_arn") !=
                identity.cloudformation_service_role_arn):
            raise AwsActionError(
                "approved deployment identities do not match the pinned AWS client")
        if deployment.get("write_freeze_seconds") != self.propagation_wait_seconds:
            raise AwsActionError(
                "approved plan does not contain the exact S3 write-freeze interval")
        namespace = context.plan.body.get("artifact_namespace")
        if not isinstance(namespace, str):
            raise AwsActionError("approved plan has no artifact namespace")
        try:
            forward = safe_resolve(
                context.artifact_root,
                f"{namespace}/workspace/{deployment['forward_template_path']}")
            rollback = safe_resolve(
                context.artifact_root,
                f"{namespace}/workspace/{deployment['rollback_template_path']}")
        except (KeyError, PathEscape, FileNotFoundError) as exc:
            raise AwsActionError(f"approved template path is invalid: {exc}") from exc
        for path, digest_name in (
            (forward, "forward_template_sha256"),
            (rollback, "rollback_template_sha256"),
        ):
            if not path.is_file() or sha256_file(path) != deployment.get(digest_name):
                raise AwsActionError("approved CloudFormation template hash does not match")
        return deployment, forward, rollback

    def preflight(self, context: ExecutionContext) -> ActionStep:
        try:
            deployment, _forward, _rollback = self._artifacts(context)
            executor_arn = self.client.assert_identity()
            stack = self.client.stack()
            status = stack.get("StackStatus")
            if status not in _STABLE_STACK_STATES:
                raise AwsActionError(f"CloudFormation stack is not stable: {status!r}")
            template = self.client.template()
            template_sha = _template_sha256(template)
            if template_sha != deployment.get("deployed_template_sha256"):
                raise AwsActionError("deployed CloudFormation template drifted after approval")
            versioning = self.client.versioning()
            expected = ("Suspended" if deployment.get("rollback_mode") == "exact"
                        else "Disabled")
            if versioning != expected:
                raise AwsActionError(
                    f"expected vulnerable pre-change versioning {expected}; "
                    f"observed {versioning}")
        except (AwsActionError, OSError, ValueError) as exc:
            return ActionStep("preflight", False, str(exc))
        return ActionStep(
            "preflight", True,
            "approved CDK intent, stack template, executor account, and live state match",
            {"resource_uid": self.client.identity.resource_uid,
             "stack_name": self.client.identity.stack_name,
             "stack_status": status, "versioning": versioning,
             "deployed_template_sha256": template_sha,
             "executor_arn": executor_arn,
             "rollback_mode": deployment.get("rollback_mode")})

    def checkpoint(self, context: ExecutionContext) -> DeploymentCheckpoint:
        deployment, _forward, _rollback = self._artifacts(context)
        template = self.client.template()
        versioning = self.client.versioning()
        return DeploymentCheckpoint(
            checkpoint_id=self.id_factory("AWSCHK"),
            detail="captured exact stack template and S3 versioning state",
            payload={
                "resource_uid": self.client.identity.resource_uid,
                "stack_name": self.client.identity.stack_name,
                "versioning": versioning,
                "template_sha256": _template_sha256(template),
                "rollback_mode": deployment.get("rollback_mode"),
            })

    def deploy(self, context: ExecutionContext,
               checkpoint: DeploymentCheckpoint) -> ActionStep:
        deployment, forward, _rollback = self._artifacts(context)
        if checkpoint.payload.get("resource_uid") != self.client.identity.resource_uid:
            return ActionStep("deploy", False, "checkpoint belongs to another AWS resource")
        if (_template_sha256(self.client.template()) !=
                checkpoint.payload.get("template_sha256")
                or self.client.versioning() != checkpoint.payload.get("versioning")):
            return ActionStep(
                "deploy", False, "AWS resource drifted after checkpoint; refusing update")
        try:
            self.client.update(forward, token=self.id_factory("AWSCFN"))
            self.client.wait_for_update()
            # AWS documents a 15-minute propagation interval after first
            # enablement. The approved operational window freezes writes for
            # this same interval; the worker does not start verification early.
            self.sleeper(self.propagation_wait_seconds)
            template_sha = _template_sha256(self.client.template())
            versioning = self.client.versioning()
            passed = (template_sha == deployment.get("forward_template_sha256")
                      and versioning == "Enabled")
        except (AwsActionError, OSError, ValueError) as exc:
            return ActionStep("deploy", False, str(exc))
        return ActionStep(
            "deploy", passed,
            ("CloudFormation enabled S3 bucket versioning" if passed else
             "CloudFormation completed without the exact approved state"),
            {"resource_uid": self.client.identity.resource_uid,
             "stack_name": self.client.identity.stack_name,
             "versioning": versioning, "template_sha256": template_sha})

    def rollback(self, context: ExecutionContext,
                 checkpoint: DeploymentCheckpoint) -> ActionStep:
        deployment, _forward, rollback = self._artifacts(context)
        if checkpoint.payload.get("resource_uid") != self.client.identity.resource_uid:
            return ActionStep("rollback", False, "checkpoint belongs to another AWS resource")
        try:
            self.client.update(rollback, token=self.id_factory("AWSCFNROLLBACK"))
            self.client.wait_for_update()
            template_sha = _template_sha256(self.client.template())
            versioning = self.client.versioning()
            contained = (template_sha == deployment.get("rollback_template_sha256")
                         and versioning == "Suspended")
        except (AwsActionError, OSError, ValueError) as exc:
            return ActionStep("rollback", False, str(exc))
        exact = deployment.get("rollback_mode") == "exact"
        return ActionStep(
            "rollback", contained,
            ("CloudFormation restored the prior Suspended versioning state" if exact else
             "CloudFormation suspended versioning; the first enablement remains irreversible"),
            {"resource_uid": self.client.identity.resource_uid,
             "versioning": versioning, "template_sha256": template_sha,
             "checkpoint_restored": bool(exact and contained),
             "containment_achieved": bool(contained),
             "rollback_mode": deployment.get("rollback_mode")})


class AwsS3VersioningHealthMonitor:
    def __init__(self, client: AwsS3CloudFormationClient) -> None:
        self.client = client

    @property
    def name(self) -> str:
        return "aws-s3-cloudformation-control-plane-health"

    def observe(self, phase: str, context: ExecutionContext) -> HealthObservation:
        try:
            stack = self.client.stack()
            versioning = self.client.versioning()
        except (AwsActionError, OSError, ValueError) as exc:
            return HealthObservation(False, (f"AWS health read failed: {exc}",), {})
        status = str(stack.get("StackStatus") or "")
        reasons = []
        if status not in _STABLE_STACK_STATES:
            reasons.append(f"CloudFormation stack status is {status or 'missing'}")
        if versioning not in {"Disabled", "Enabled", "Suspended"}:
            reasons.append(f"S3 versioning status is {versioning}")
        return HealthObservation(
            not reasons, tuple(reasons) or (f"AWS control plane is healthy during {phase}",),
            {"stack_status": status, "versioning": versioning})


class AwsS3VersioningProbe:
    def __init__(self, client: AwsS3CloudFormationClient) -> None:
        self.client = client

    @property
    def name(self) -> str:
        return "aws-s3-versioning-enabled"

    def run(self, context: ExecutionContext) -> ProbeResult:
        actual = self.client.versioning()
        return ProbeResult(
            probe=self.name, target=self.client.identity.resource_uid,
            passed=actual == "Enabled",
            detail=("S3 bucket versioning is enabled" if actual == "Enabled" else
                    "S3 bucket versioning is not enabled"),
            payload={"expected": "Enabled", "actual": actual})
