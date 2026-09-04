"""Narrow AWS CDK/CloudFormation planning for S3 bucket versioning.

This module deliberately supports one construct shape and one CloudFormation
change.  It is not a general TypeScript editor or a general CloudFormation
deployment engine.  The live stack template is the state anchor; synthesis is
admitted only when removing the proposed VersioningConfiguration makes the
template byte-for-byte equivalent (after canonical JSON normalization) to that
anchor.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .hashing import canonical_json, sha256_bytes, sha256_file


class AwsCdkPlanningError(ValueError):
    pass


_S3_ARN = re.compile(
    r"^arn:(?P<partition>aws|aws-us-gov|aws-cn):s3:::(?P<bucket>[^/]+)$")
_ACCOUNT = re.compile(r"^[0-9]{12}$")
_REGION = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-[0-9]+$")
_ROLE_ARN = re.compile(
    r"^arn:(?:aws|aws-us-gov|aws-cn):iam::(?P<account>[0-9]{12}):role/.+$")
_IGNORED = frozenset({
    ".git", "node_modules", "cdk.out", "dist", "build", ".venv",
    "__pycache__",
})


@dataclass(frozen=True)
class AwsCdkLink:
    resource_uid: str
    source_path: str
    module_path: str
    resource_type: str
    resource_name: str
    start_line: int
    end_line: int
    match_strategy: str
    confidence: float
    source_sha256: str
    resource_address: str
    state_sha256: str
    iac_engine: str
    stack_name: str
    logical_resource_id: str
    construct_id: str
    account_id: str
    region: str
    executor_role_arn: str
    cloudformation_service_role_arn: str | None
    rollback_mode: str

    def to_dict(self) -> dict:
        return {
            "resource_uid": self.resource_uid,
            "source_path": self.source_path,
            "module_path": self.module_path,
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "match_strategy": self.match_strategy,
            "confidence": self.confidence,
            "source_sha256": self.source_sha256,
            "resource_address": self.resource_address,
            "state_sha256": self.state_sha256,
            "iac_engine": self.iac_engine,
            "stack_name": self.stack_name,
            "logical_resource_id": self.logical_resource_id,
            "construct_id": self.construct_id,
            "account_id": self.account_id,
            "region": self.region,
            "executor_role_arn": self.executor_role_arn,
            "cloudformation_service_role_arn": self.cloudformation_service_role_arn,
            "rollback_mode": self.rollback_mode,
        }


def _state(document: Mapping | None) -> tuple[dict, dict]:
    if not isinstance(document, Mapping):
        raise AwsCdkPlanningError("AWS CDK planning requires a state document")
    if document.get("format") != "ElCapitanAwsCdkState.v1":
        raise AwsCdkPlanningError(
            "AWS CDK state format must be ElCapitanAwsCdkState.v1")
    required_strings = (
        "stack_name", "logical_resource_id", "construct_id", "source_path",
        "module_path", "source_sha256", "account_id", "region",
        "executor_role_arn",
    )
    missing = [name for name in required_strings
               if not isinstance(document.get(name), str) or not document[name]]
    if missing:
        raise AwsCdkPlanningError(
            "AWS CDK state is missing: " + ", ".join(missing))
    if not _ACCOUNT.fullmatch(str(document["account_id"])):
        raise AwsCdkPlanningError("AWS CDK state has an invalid account_id")
    if not _REGION.fullmatch(str(document["region"])):
        raise AwsCdkPlanningError("AWS CDK state has an invalid region")
    executor = _ROLE_ARN.fullmatch(str(document["executor_role_arn"]))
    if not executor or executor.group("account") != document["account_id"]:
        raise AwsCdkPlanningError("AWS CDK state has an invalid executor role")
    if "cloudformation_service_role_arn" not in document:
        raise AwsCdkPlanningError(
            "AWS CDK state must record the CloudFormation service-role baseline")
    service_role = document["cloudformation_service_role_arn"]
    if service_role is not None:
        match = _ROLE_ARN.fullmatch(str(service_role))
        if not match or match.group("account") != document["account_id"]:
            raise AwsCdkPlanningError(
                "AWS CDK state has an invalid CloudFormation service role")
    template = document.get("deployed_template")
    if not isinstance(template, Mapping):
        raise AwsCdkPlanningError("AWS CDK state has no deployed template object")
    resources = template.get("Resources")
    if not isinstance(resources, Mapping):
        raise AwsCdkPlanningError("deployed template has no Resources object")
    logical_id = str(document["logical_resource_id"])
    resource = resources.get(logical_id)
    if not isinstance(resource, Mapping) or resource.get("Type") != "AWS::S3::Bucket":
        raise AwsCdkPlanningError(
            "deployed template logical resource is not an AWS::S3::Bucket")
    properties = resource.get("Properties")
    if not isinstance(properties, Mapping):
        raise AwsCdkPlanningError("deployed S3 resource has no Properties object")
    return dict(document), deepcopy(dict(template))


def _typescript_files(root: Path) -> tuple[Path, ...]:
    files = []
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            name for name in directories
            if name not in _IGNORED and not (current_path / name).is_symlink())
        for name in sorted(names):
            path = current_path / name
            if path.suffix == ".ts" and path.is_file() and not path.is_symlink():
                files.append(path)
    return tuple(files)


def _matching_construct(text: str, construct_id: str) -> tuple[int, int] | None:
    header = re.compile(
        r"new\s+s3\.Bucket\s*\(\s*this\s*,\s*"
        + re.escape(repr(construct_id))
        + r"\s*,\s*\{")
    matches = list(header.finditer(text))
    if not matches:
        # Accept the equivalent double-quoted spelling while retaining an
        # exact literal construct id.
        header = re.compile(
            r'new\s+s3\.Bucket\s*\(\s*this\s*,\s*"'
            + re.escape(construct_id)
            + r'"\s*,\s*\{')
        matches = list(header.finditer(text))
    if len(matches) > 1:
        raise AwsCdkPlanningError(
            f"multiple s3.Bucket constructs use id {construct_id!r}")
    if not matches:
        return None
    start = matches[0].start()
    open_brace = text.find("{", matches[0].start(), matches[0].end())
    depth = 0
    quote = ""
    escaped = False
    line_comment = False
    block_comment = False
    index = open_brace
    while index < len(text):
        char = text[index]
        following = text[index:index + 2]
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if following == "*/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        elif following == "//":
            line_comment = True
            index += 1
        elif following == "/*":
            block_comment = True
            index += 1
        elif char in {"'", '"', "`"}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                # Include the closing call and semicolon when present.
                close = index + 1
                suffix = re.match(r"\s*\)\s*;?", text[close:])
                return start, close + (suffix.end() if suffix else 0)
        index += 1
    raise AwsCdkPlanningError(
        f"unterminated s3.Bucket construct {construct_id!r}")


def link_aws_cdk_s3_bucket(repository, *, provider: str, resource_uid: str,
                           state_document: Mapping | None = None,
                           resource_types: tuple[str, ...] = ()) -> AwsCdkLink:
    """Link one exact deployed S3 bucket to one CDK construct."""
    if provider != "aws":
        raise AwsCdkPlanningError("AWS CDK linker accepts only provider 'aws'")
    match = _S3_ARN.fullmatch(resource_uid)
    if not match:
        raise AwsCdkPlanningError("AWS CDK target is not a bucket-level S3 ARN")
    document, template = _state(state_document)
    logical_id = document["logical_resource_id"]
    properties = template["Resources"][logical_id]["Properties"]
    if properties.get("BucketName") != match.group("bucket"):
        raise AwsCdkPlanningError(
            "deployed template bucket name does not match the finding resource")
    versioning = properties.get("VersioningConfiguration")
    if versioning is not None and (
            not isinstance(versioning, Mapping)
            or versioning.get("Status") not in {"Enabled", "Suspended"}):
        raise AwsCdkPlanningError(
            "deployed template has an invalid VersioningConfiguration")
    if isinstance(versioning, Mapping) and versioning.get("Status") == "Enabled":
        raise AwsCdkPlanningError(
            "deployed template already enables S3 versioning")

    root = Path(repository).resolve(strict=True)
    requested = (root / str(document["source_path"])).resolve(strict=True)
    if not requested.is_relative_to(root) or requested.is_symlink():
        raise AwsCdkPlanningError("AWS CDK source path escapes the repository")
    if requested not in _typescript_files(root):
        raise AwsCdkPlanningError("AWS CDK source path is not an eligible TypeScript file")
    module = (root / str(document["module_path"])).resolve(strict=True)
    if not module.is_relative_to(root) or not module.is_dir() or module.is_symlink():
        raise AwsCdkPlanningError("AWS CDK module path escapes the repository")
    if not requested.is_relative_to(module):
        raise AwsCdkPlanningError("AWS CDK source path is outside the module path")
    text = requested.read_text(encoding="utf-8")
    if len(text.encode("utf-8")) > 2 * 1024 * 1024:
        raise AwsCdkPlanningError("AWS CDK source exceeds 2 MiB")
    source_sha256 = sha256_file(requested)
    if source_sha256 != document["source_sha256"]:
        raise AwsCdkPlanningError(
            "AWS CDK source digest does not match the state document")
    bounds = _matching_construct(text, str(document["construct_id"]))
    if bounds is None:
        raise AwsCdkPlanningError(
            f"no s3.Bucket construct uses id {document['construct_id']!r}")
    start, end = bounds
    start_line = text.count("\n", 0, start) + 1
    end_line = text.count("\n", 0, end) + 1
    relative = requested.relative_to(root).as_posix()
    return AwsCdkLink(
        resource_uid=resource_uid,
        source_path=relative,
        module_path=module.relative_to(root).as_posix(),
        resource_type="AWS::S3::Bucket",
        resource_name=str(document["construct_id"]),
        start_line=start_line,
        end_line=end_line,
        match_strategy="cloudformation_stack_logical_id_and_cdk_construct",
        confidence=1.0,
        source_sha256=source_sha256,
        resource_address=f"{document['stack_name']}.{logical_id}",
        state_sha256=sha256_bytes(canonical_json(document)),
        iac_engine="aws_cdk_cloudformation",
        stack_name=str(document["stack_name"]),
        logical_resource_id=str(logical_id),
        construct_id=str(document["construct_id"]),
        account_id=str(document["account_id"]),
        region=str(document["region"]),
        executor_role_arn=str(document["executor_role_arn"]),
        cloudformation_service_role_arn=(
            str(document["cloudformation_service_role_arn"])
            if document["cloudformation_service_role_arn"] is not None else None),
        rollback_mode=("exact" if isinstance(versioning, Mapping) else "containment"),
    )


def materialize_cdk_s3_versioning(*, original: str, proposed: str,
                                  link: AwsCdkLink) -> str:
    """Insert exactly one ``versioned: true`` in the linked construct."""
    proposed_bounds = _matching_construct(proposed, link.construct_id)
    if proposed_bounds is None or not re.search(
            r"(?m)^\s*versioned\s*:\s*true\s*,?\s*(?://.*)?$",
            proposed[proposed_bounds[0]:proposed_bounds[1]]):
        raise AwsCdkPlanningError(
            "agent proposal did not request versioned: true in the linked construct")
    bounds = _matching_construct(original, link.construct_id)
    if bounds is None:
        raise AwsCdkPlanningError("linked CDK construct disappeared")
    block = original[bounds[0]:bounds[1]]
    if re.search(r"(?m)^\s*versioned\s*:", block):
        raise AwsCdkPlanningError(
            "linked CDK construct already has an explicit versioned property")
    encryption = list(re.finditer(r"(?m)^(?P<indent>\s*)encryption\s*:.*(?:\n|$)", block))
    if len(encryption) != 1:
        raise AwsCdkPlanningError(
            "linked CDK construct must contain exactly one encryption property")
    insertion = encryption[0].end()
    indent = encryption[0].group("indent")
    changed_block = block[:insertion] + f"{indent}versioned:         true,\n" + block[insertion:]
    return original[:bounds[0]] + changed_block + original[bounds[1]:]


def verify_s3_versioning_template_change(*, deployed_template: Mapping,
                                         proposed_template: Mapping,
                                         logical_resource_id: str,
                                         baseline_synthesized_template: Mapping | None = None,
                                         ) -> tuple[dict, dict]:
    """Return canonical forward/containment templates after exact-scope proof."""
    deployed = deepcopy(dict(deployed_template))
    proposed = deepcopy(dict(proposed_template))
    baseline = deepcopy(dict(
        baseline_synthesized_template or deployed_template))
    for name, template in (
            ("deployed", deployed), ("baseline", baseline),
            ("proposed", proposed)):
        resources = template.get("Resources")
        if not isinstance(resources, Mapping):
            raise AwsCdkPlanningError(f"{name} template has no Resources object")
        resource = resources.get(logical_resource_id)
        if not isinstance(resource, Mapping) or resource.get("Type") != "AWS::S3::Bucket":
            raise AwsCdkPlanningError(
                f"{name} template target is not an AWS::S3::Bucket")
        if not isinstance(resource.get("Properties"), Mapping):
            raise AwsCdkPlanningError(f"{name} template target has no Properties")
    deployed_properties = deployed["Resources"][logical_resource_id]["Properties"]
    baseline_properties = baseline["Resources"][logical_resource_id]["Properties"]
    proposed_properties = proposed["Resources"][logical_resource_id]["Properties"]
    prior = deployed_properties.get("VersioningConfiguration")
    if prior is not None and (
            not isinstance(prior, Mapping) or prior.get("Status") != "Suspended"):
        raise AwsCdkPlanningError(
            "deployed versioning state must be absent or Suspended")
    if proposed_properties.get("VersioningConfiguration") != {"Status": "Enabled"}:
        raise AwsCdkPlanningError(
            "proposed template must set only VersioningConfiguration.Status=Enabled")
    baseline_versioning = baseline_properties.get("VersioningConfiguration")
    if baseline_versioning is not None and baseline_versioning != prior:
        raise AwsCdkPlanningError(
            "baseline synthesis changes the deployed S3 versioning property")
    comparison = deepcopy(proposed)
    comparison_properties = comparison["Resources"][logical_resource_id]["Properties"]
    if baseline_versioning is None:
        comparison_properties.pop("VersioningConfiguration", None)
    else:
        comparison_properties["VersioningConfiguration"] = deepcopy(
            baseline_versioning)
    if canonical_json(comparison) != canonical_json(baseline):
        raise AwsCdkPlanningError(
            "synthesized template changes content outside the approved S3 versioning property")
    # Deploy from the live processed template rather than carrying unrelated
    # pre-existing source/template drift into this action.
    forward = deepcopy(deployed)
    forward["Resources"][logical_resource_id]["Properties"][
        "VersioningConfiguration"] = {"Status": "Enabled"}
    rollback = deepcopy(forward)
    rollback["Resources"][logical_resource_id]["Properties"][
        "VersioningConfiguration"] = {"Status": "Suspended"}
    return forward, rollback


class AwsCdkCloudFormationRunner:
    """Synthesize CDK without cloud credentials and prove the template scope."""

    def __init__(self, executable: tuple[str, ...] = (
            "npx", "--no-install", "cdk"), *,
                 timeout_seconds: float = 300,
                 application_environment: Mapping[str, str] | None = None) -> None:
        if not executable or timeout_seconds <= 0:
            raise ValueError("CDK executable and positive timeout are required")
        self.executable = tuple(executable)
        self.timeout_seconds = timeout_seconds
        self.application_environment = dict(application_environment or {})

    @staticmethod
    def _bounded(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        return value[:1_000_000]

    def _run(self, name, argv, *, module, environment, TerraformCheck):
        try:
            completed = subprocess.run(
                argv, cwd=module, env=environment, capture_output=True,
                text=True, check=False, timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            return TerraformCheck(
                name, argv, 124, self._bounded(exc.stdout),
                self._bounded(exc.stderr) +
                f"\n{name} timed out after {self.timeout_seconds}s")
        except OSError as exc:
            return TerraformCheck(name, argv, 127, stderr=str(exc))
        return TerraformCheck(
            name, argv, completed.returncode,
            self._bounded(completed.stdout), self._bounded(completed.stderr))

    @staticmethod
    def _dependency_command(module: Path) -> tuple[str, ...]:
        if (module / "pnpm-lock.yaml").is_file():
            return (
                "pnpm", "install", "--frozen-lockfile", "--ignore-scripts",
                "--reporter=silent")
        if (module / "package-lock.json").is_file():
            return ("npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund")
        raise AwsCdkPlanningError(
            "CDK module requires pnpm-lock.yaml or package-lock.json")

    def check(self, workspace: Path, link: AwsCdkLink, *,
              state_document: Mapping | None = None,
              original_source: str | None = None):
        # Local import avoids coupling the pure linker to Terraform internals
        # while retaining the existing generic planning-check record shape.
        from .remediation_planning import TerraformCheck

        document, deployed_template = _state(state_document)
        if (document["stack_name"] != link.stack_name
                or document["logical_resource_id"] != link.logical_resource_id
                or document["account_id"] != link.account_id
                or document["region"] != link.region):
            return (TerraformCheck(
                "cdk_synth", self.executable, 1,
                stderr="AWS CDK state does not match the linked target"),)
        module = (workspace / link.module_path).resolve(strict=True)
        if not module.is_relative_to(workspace.resolve(strict=True)):
            return (TerraformCheck(
                "cdk_synth", self.executable, 1,
                stderr="AWS CDK module path escapes the planning workspace"),)
        source = (workspace / link.source_path).resolve(strict=True)
        if (not source.is_relative_to(module) or original_source is None
                or sha256_bytes(original_source.encode("utf-8")) !=
                link.source_sha256):
            return (TerraformCheck(
                "cdk_baseline_synth", self.executable, 1,
                stderr="original CDK source does not match the approved link"),)
        replacement_source = source.read_text(encoding="utf-8")
        dependency_path = module / "node_modules"
        if dependency_path.exists() or dependency_path.is_symlink():
            return (TerraformCheck(
                "dependency_install", ("locked-package-manager",), 1,
                stderr="copied CDK workspace unexpectedly contains node_modules"),)
        environment = {
            key: value for key, value in self.application_environment.items()
            if isinstance(key, str) and isinstance(value, str)
        }
        for name in (
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
            "AWS_PROFILE", "AWS_DEFAULT_PROFILE", "AWS_ROLE_ARN",
            "AWS_WEB_IDENTITY_TOKEN_FILE", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY", "GOOGLE_API_KEY", "AZURE_CLIENT_SECRET",
            "AWS_CONTAINER_CREDENTIALS_FULL_URI",
            "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
        ):
            environment.pop(name, None)
        environment.update({
            "CDK_DEFAULT_ACCOUNT": link.account_id,
            "CDK_DEFAULT_REGION": link.region,
            "AWS_REGION": link.region,
            "AWS_EC2_METADATA_DISABLED": "true",
            "CI": "true",
        })
        if "PATH" in os.environ:
            environment["PATH"] = os.environ["PATH"]
        checks = []
        with tempfile.TemporaryDirectory(prefix="elcapitan-cdk-") as temporary:
            home = Path(temporary) / "home"
            home.mkdir()
            environment.update({
                "HOME": str(home),
                "AWS_SHARED_CREDENTIALS_FILE": os.devnull,
                "AWS_CONFIG_FILE": os.devnull,
            })
            try:
                dependency_argv = self._dependency_command(module)
            except AwsCdkPlanningError as exc:
                return (TerraformCheck(
                    "dependency_install", ("locked-package-manager",), 1,
                    stderr=str(exc)),)
            dependency = self._run(
                "dependency_install", dependency_argv, module=module,
                environment=environment, TerraformCheck=TerraformCheck)
            checks.append(dependency)
            if not dependency.passed:
                return tuple(checks)
            synth_results = []
            try:
                for name, content in (
                        ("cdk_baseline_synth", original_source),
                        ("cdk_synth", replacement_source)):
                    source.write_text(content, encoding="utf-8")
                    output = str(Path(temporary) / name)
                    argv = (*self.executable, "synth", link.stack_name, "--json",
                            "--exclusively", "--no-lookups", "--output", output)
                    result = self._run(
                        name, argv, module=module, environment=environment,
                        TerraformCheck=TerraformCheck)
                    checks.append(result)
                    if not result.passed:
                        return tuple(checks)
                    synth_results.append(result)
            finally:
                source.write_text(replacement_source, encoding="utf-8")
                if dependency_path.is_dir() and not dependency_path.is_symlink():
                    shutil.rmtree(dependency_path)
        baseline_synth, proposed_synth = synth_results
        try:
            baseline = json.loads(baseline_synth.stdout)
            proposed = json.loads(proposed_synth.stdout)
            if not isinstance(baseline, Mapping) or not isinstance(proposed, Mapping):
                raise AwsCdkPlanningError("CDK output is not a template object")
            forward, rollback = verify_s3_versioning_template_change(
                deployed_template=deployed_template,
                proposed_template=proposed,
                logical_resource_id=link.logical_resource_id,
                baseline_synthesized_template=baseline)
        except (json.JSONDecodeError, AwsCdkPlanningError) as exc:
            return (*checks, TerraformCheck(
                "cloudformation_scope", ("deterministic-template-diff",), 1,
                stderr=str(exc)))
        checks = [
            TerraformCheck(
                check.name, check.argv, check.exit_code,
                stdout="CDK synthesized an ephemeral CloudFormation template.",
                stderr=check.stderr)
            if check.name in {"cdk_baseline_synth", "cdk_synth"}
            else check
            for check in checks
        ]
        artifacts = workspace / ".elcapitan-plan"
        artifacts.mkdir(exist_ok=False)
        forward_path = artifacts / "forward-template.json"
        rollback_path = artifacts / "containment-template.json"
        forward_path.write_bytes(canonical_json(forward))
        rollback_path.write_bytes(canonical_json(rollback))
        details = {
            "stack_name": link.stack_name,
            "logical_resource_id": link.logical_resource_id,
            "account_id": link.account_id,
            "region": link.region,
            "executor_role_arn": link.executor_role_arn,
            "cloudformation_service_role_arn": link.cloudformation_service_role_arn,
            "forward_template_path": forward_path.relative_to(workspace).as_posix(),
            "forward_template_sha256": sha256_file(forward_path),
            "rollback_template_path": rollback_path.relative_to(workspace).as_posix(),
            "rollback_template_sha256": sha256_file(rollback_path),
            "deployed_template_sha256": sha256_bytes(canonical_json(deployed_template)),
            "baseline_synthesized_template_sha256": sha256_bytes(
                canonical_json(baseline)),
            "preexisting_source_template_drift": (
                canonical_json(baseline) != canonical_json(deployed_template)),
            "rollback_mode": link.rollback_mode,
            "write_freeze_seconds": 900,
            "approved_change": (
                f"Resources.{link.logical_resource_id}."
                "Properties.VersioningConfiguration.Status"),
        }
        return (
            *checks,
            TerraformCheck(
                "cloudformation_scope", ("deterministic-template-diff",), 0,
                stdout="Only the linked bucket versioning status changes.",
                details=details),
            TerraformCheck(
                "rollback_template", ("deterministic-containment-template",), 0,
                stdout=("Containment template pins versioning to Suspended; "
                        "first enablement is irreversible."),
                details={
                    "rollback_mode": link.rollback_mode,
                    "checkpoint_restorable": link.rollback_mode == "exact",
                }),
        )
