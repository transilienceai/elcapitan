import json
import os
from pathlib import Path

import pytest

from elcapitan.action_plane import (
    ActionStep,
    DeploymentCheckpoint,
    ExecutionContext,
    ExecutionService,
    HealthObservation,
)
from elcapitan.agents import RecordedContractRuntime
from elcapitan.aws_action import (
    AwsActionError,
    AwsCommandResult,
    AwsS3CloudFormationClient,
    AwsS3CloudFormationIdentity,
    AwsS3VersioningCloudFormationDriver,
    AwsS3VersioningHealthMonitor,
    AwsS3VersioningProbe,
    SubprocessAwsCommandRunner,
    aws_executor_environment,
)
from elcapitan.case_store import SqliteCaseStore
from elcapitan.cases import CaseState, ChangeWindow, RemediationCase
from elcapitan.hashing import canonical_json, sha256_bytes, sha256_file
from elcapitan.product_records import ProductRecord, SqliteProductRecordStore

ACCOUNT = "111122223333"
BUCKET = "training-assets"
BUCKET_ARN = f"arn:aws:s3:::{BUCKET}"
STACK = "TrainingStatic"
LOGICAL_ID = "AssetsBucketA1B2C3"
REGION = "us-east-1"
EXECUTOR_ROLE = f"arn:aws:iam::{ACCOUNT}:role/elcapitan-s3-versioning-executor"


def template(status=None):
    properties = {"BucketName": BUCKET, "BucketEncryption": {"mode": "AES256"}}
    if status:
        properties["VersioningConfiguration"] = {"Status": status}
    return {"Resources": {LOGICAL_ID: {
        "Type": "AWS::S3::Bucket", "Properties": properties,
    }}}


class FakeClient:
    def __init__(self):
        self.identity = AwsS3CloudFormationIdentity(
            BUCKET_ARN, BUCKET, ACCOUNT, REGION, STACK, LOGICAL_ID,
            EXECUTOR_ROLE, None)
        self.current_template = template()
        self.current_versioning = "Disabled"
        self.pending_template = None
        self.updates = []

    def assert_identity(self):
        return f"arn:aws:sts::{ACCOUNT}:assumed-role/elcapitan-executor/session"

    def stack(self):
        return {
            "StackId": f"arn:aws:cloudformation:{REGION}:{ACCOUNT}:stack/{STACK}/id",
            "StackStatus": "UPDATE_COMPLETE",
            "RoleARN": None,
        }

    def template(self):
        return self.current_template

    def versioning(self):
        return self.current_versioning

    def update(self, path, *, token):
        self.pending_template = json.loads(path.read_text(encoding="utf-8"))
        self.updates.append((path.name, token))

    def wait_for_update(self):
        self.current_template = self.pending_template
        status = self.current_template["Resources"][LOGICAL_ID]["Properties"][
            "VersioningConfiguration"]["Status"]
        self.current_versioning = status


def context(tmp_path: Path):
    namespace = "cases/CASE-1/planning/PLAN-1"
    artifact_dir = tmp_path / namespace / "workspace" / ".elcapitan-plan"
    artifact_dir.mkdir(parents=True)
    forward = artifact_dir / "forward-template.json"
    rollback = artifact_dir / "containment-template.json"
    forward.write_bytes(canonical_json(template("Enabled")))
    rollback.write_bytes(canonical_json(template("Suspended")))
    deployment = {
        "stack_name": STACK,
        "logical_resource_id": LOGICAL_ID,
        "account_id": ACCOUNT,
        "region": REGION,
        "executor_role_arn": EXECUTOR_ROLE,
        "cloudformation_service_role_arn": None,
        "forward_template_path": ".elcapitan-plan/forward-template.json",
        "forward_template_sha256": sha256_file(forward),
        "rollback_template_path": ".elcapitan-plan/containment-template.json",
        "rollback_template_sha256": sha256_file(rollback),
        "deployed_template_sha256": sha256_bytes(canonical_json(template())),
        "rollback_mode": "containment",
        "write_freeze_seconds": 900,
        "approved_change": (
            f"Resources.{LOGICAL_ID}.Properties.VersioningConfiguration.Status"),
    }
    case = RemediationCase(
        "CASE-1", "TEN-1", ("FIND-1",), (BUCKET_ARN,), ("shasta",),
        CaseState.APPROVED, 1, "2026-09-03T00:00:00Z", "2026-09-03T00:00:00Z")
    plan = ProductRecord(
        "PLAN-1", "CASE-1", "RemediationPlan.v1", 1,
        "2026-09-03T00:00:00Z",
        {"status": "verified", "artifact_namespace": namespace,
         "deployment": deployment, "change": {},
         "scope": {"finding_ids": ["FIND-1"]}})
    link = ProductRecord(
        "LINK-1", "CASE-1", "IaCLink.v1", 1, "2026-09-03T00:00:00Z",
        {"link": {
            "resource_uid": BUCKET_ARN,
            "iac_engine": "aws_cdk_cloudformation",
            "stack_name": STACK,
            "logical_resource_id": LOGICAL_ID,
            "account_id": ACCOUNT,
            "region": REGION,
            "executor_role_arn": EXECUTOR_ROLE,
            "cloudformation_service_role_arn": None,
        }})
    placeholder = ProductRecord(
        "RECORD-1", "CASE-1", "Placeholder.v1", 1,
        "2026-09-03T00:00:00Z", {})
    return ExecutionContext(case, plan, link, placeholder, placeholder, tmp_path)


def test_aws_driver_enables_and_contains_irreversible_versioning(tmp_path):
    client = FakeClient()
    ctx = context(tmp_path)
    sleeps = []
    driver = AwsS3VersioningCloudFormationDriver(
        client, id_factory=lambda prefix: prefix + "-1",
        sleeper=sleeps.append)
    assert driver.preflight(ctx).passed
    checkpoint = driver.checkpoint(ctx)
    assert checkpoint.payload["versioning"] == "Disabled"
    assert driver.deploy(ctx, checkpoint).passed
    assert client.current_versioning == "Enabled"
    assert sleeps == [900]
    assert AwsS3VersioningProbe(client).run(ctx).passed
    assert AwsS3VersioningHealthMonitor(client).observe(
        "after_deploy", ctx).healthy
    rollback = driver.rollback(ctx, checkpoint)
    assert rollback.passed
    assert rollback.payload["containment_achieved"] is True
    assert rollback.payload["checkpoint_restored"] is False
    assert client.current_versioning == "Suspended"
    assert [name for name, _token in client.updates] == [
        "forward-template.json", "containment-template.json"]


def test_aws_driver_refuses_stack_template_drift(tmp_path):
    client = FakeClient()
    ctx = context(tmp_path)
    client.current_template["Resources"][LOGICAL_ID]["Properties"][
        "Unexpected"] = True
    result = AwsS3VersioningCloudFormationDriver(client).preflight(ctx)
    assert not result.passed
    assert "drifted" in result.detail
    assert client.updates == []


def test_executor_environment_is_complete_and_excludes_profiles(monkeypatch):
    host = {
        "ELCAP_EXECUTOR_AWS_ACCESS_KEY_ID": "executor-id",
        "ELCAP_EXECUTOR_AWS_SECRET_ACCESS_KEY": "executor-secret",
        "ELCAP_EXECUTOR_AWS_SESSION_TOKEN": "executor-session",
        "AWS_PROFILE": "admin",
        "OPENAI_API_KEY": "must-not-pass",
        "PATH": os.environ["PATH"],
    }
    environment = aws_executor_environment(host)
    assert environment["AWS_ACCESS_KEY_ID"] == "executor-id"
    assert "AWS_PROFILE" not in environment
    assert "OPENAI_API_KEY" not in environment
    assert "HOME" not in environment
    assert environment["AWS_SHARED_CREDENTIALS_FILE"] == os.devnull
    assert environment["AWS_CONFIG_FILE"] == os.devnull
    runner = SubprocessAwsCommandRunner(host_env=host)
    assert runner.environment == environment


def test_subprocess_runner_refreshes_executor_environment_for_every_call(monkeypatch):
    issued = iter(("first-session", "second-session"))
    environments = []

    def provider():
        token = next(issued)
        return {
            "ELCAP_EXECUTOR_AWS_ACCESS_KEY_ID": "executor-id",
            "ELCAP_EXECUTOR_AWS_SECRET_ACCESS_KEY": "executor-secret",
            "ELCAP_EXECUTOR_AWS_SESSION_TOKEN": token,
        }

    def run(argv, **kwargs):
        environments.append(kwargs["env"])
        return type("Completed", (), {
            "returncode": 0, "stdout": "{}", "stderr": "",
        })()

    monkeypatch.setattr("elcapitan.aws_action.subprocess.run", run)
    runner = SubprocessAwsCommandRunner(host_env=provider)
    assert runner.run(("sts", "get-caller-identity")).exit_code == 0
    assert runner.run(("s3api", "get-bucket-versioning")).exit_code == 0
    assert [environment["AWS_SESSION_TOKEN"] for environment in environments] == [
        "first-session", "second-session"]


class QueueRunner:
    def __init__(self, documents):
        self.documents = list(documents)
        self.calls = []

    def run(self, argv, *, timeout_seconds=None):
        self.calls.append((argv, timeout_seconds))
        document = self.documents.pop(0)
        return AwsCommandResult(0, json.dumps(document))


def aws_client(runner):
    return AwsS3CloudFormationClient(
        BUCKET_ARN, account_id=ACCOUNT, region=REGION, stack_name=STACK,
        logical_resource_id=LOGICAL_ID, executor_role_arn=EXECUTOR_ROLE,
        cloudformation_service_role_arn=None, runner=runner)


def test_aws_client_pins_exact_assumed_role_and_stack_service_role():
    runner = QueueRunner([
        {"Account": ACCOUNT, "Arn": (
            f"arn:aws:sts::{ACCOUNT}:assumed-role/"
            "elcapitan-s3-versioning-executor/one-shot")},
        {"Stacks": [{
            "StackId": (
                f"arn:aws:cloudformation:{REGION}:{ACCOUNT}:stack/{STACK}/id"),
            "StackStatus": "UPDATE_COMPLETE",
        }]},
    ])
    client = aws_client(runner)
    assert client.assert_identity().endswith("/one-shot")
    assert client.stack()["StackStatus"] == "UPDATE_COMPLETE"

    wrong_role = QueueRunner([{
        "Account": ACCOUNT,
        "Arn": f"arn:aws:sts::{ACCOUNT}:assumed-role/administrator/session",
    }])
    with pytest.raises(AwsActionError, match="not the pinned"):
        aws_client(wrong_role).assert_identity()

    changed_service_role = QueueRunner([{"Stacks": [{
        "StackId": f"arn:aws:cloudformation:{REGION}:{ACCOUNT}:stack/{STACK}/id",
        "StackStatus": "UPDATE_COMPLETE",
        "RoleARN": f"arn:aws:iam::{ACCOUNT}:role/unapproved-service-role",
    }]}])
    with pytest.raises(AwsActionError, match="service role differs"):
        aws_client(changed_service_role).stack()


def test_aws_client_does_not_attach_a_service_role_during_update(tmp_path):
    forward = tmp_path / "forward.json"
    forward.write_text(json.dumps(template("Enabled")), encoding="utf-8")
    runner = QueueRunner([{
        "StackId": f"arn:aws:cloudformation:{REGION}:{ACCOUNT}:stack/{STACK}/id",
    }])
    aws_client(runner).update(forward, token="AWSCFN-1")
    argv, _timeout = runner.calls[0]
    assert "update-stack" in argv
    assert "--role-arn" not in argv


class ContainmentDriver:
    name = "containment-test-driver"

    def rollback(self, context, checkpoint):
        return ActionStep(
            "rollback", True, "irreversible change contained",
            {"checkpoint_restored": False, "containment_achieved": True})


class HealthyMonitor:
    name = "healthy-test-monitor"

    def observe(self, phase, context):
        return HealthObservation(True, ("healthy",), {})


def test_execution_service_records_containment_without_claiming_restoration(tmp_path):
    database = tmp_path / "product.db"
    cases = SqliteCaseStore(database)
    records = SqliteProductRecordStore(database)
    ctx = context(tmp_path)
    executing = RemediationCase(
        **{**ctx.case.__dict__, "state": CaseState.EXECUTING})
    cases.create(executing)
    counts = {}

    def ids(prefix):
        counts[prefix] = counts.get(prefix, 0) + 1
        return f"{prefix}-{counts[prefix]:03d}"

    service = ExecutionService(
        case_store=cases, record_store=records, artifact_root=tmp_path,
        driver=ContainmentDriver(), monitor=HealthyMonitor(), probes=(),
        runtime=RecordedContractRuntime({}, now=lambda: "2026-09-03T00:00:00Z"),
        now=lambda: "2026-09-03T00:00:00Z",
        id_factory=ids)
    outcome = service._rollback(
        executing.case_id, ctx,
        DeploymentCheckpoint("CHK-1", "captured", {}),
        tmp_path / "execution", (), "verification failed")
    assert outcome.case.state is CaseState.BLOCKED
    assert outcome.case.blocked_from is CaseState.ROLLING_BACK
    assert outcome.rolled_back is False
    assert outcome.contained is True
    assert outcome.verification_record.body["checkpoint_restored"] is False
    assert outcome.verification_record.body["containment_achieved"] is True


def test_aws_driver_reaches_completion_certificate_after_approved_execution(tmp_path):
    database = tmp_path / "product.db"
    cases = SqliteCaseStore(database)
    records = SqliteProductRecordStore(database)
    ctx = context(tmp_path)
    window = ChangeWindow(
        "WIN-1", "2026-09-02T23:59:00Z", "2026-09-03T00:30:00Z", "UTC",
        ("approved production write freeze",), (), 1.0)
    approved = RemediationCase(
        case_id=ctx.case.case_id, tenant_id=ctx.case.tenant_id,
        finding_ids=ctx.case.finding_ids, asset_ids=ctx.case.asset_ids,
        service_ids=ctx.case.service_ids, state=CaseState.APPROVED, version=1,
        created_at=ctx.case.created_at, updated_at=ctx.case.updated_at,
        change_window=window,
        record_ids={
            "change_plan_id": ctx.plan.record_id,
            "iac_link_id": ctx.link.record_id,
            "approval_id": "APPROVAL-1",
            "change_window_id": "WIN-1",
            "schedule_id": "SCHEDULE-1",
            "execution_job_id": "JOB-1",
        })
    approval = ProductRecord(
        "APPROVAL-1", approved.case_id, "ChangeApproval.v1", 1,
        "2026-09-03T00:00:00Z",
        {"expires_at": "2026-09-03T00:30:00Z"})
    window_record = ProductRecord(
        "WIN-1", approved.case_id, "ChangeWindowRecommendation.v1", 1,
        "2026-09-03T00:00:00Z", {"window_id": "WIN-1"})
    for record in (ctx.plan, ctx.link, approval, window_record):
        records.put(record)
    cases.create(approved)
    counts = {}

    def ids(prefix):
        counts[prefix] = counts.get(prefix, 0) + 1
        return f"{prefix}-{counts[prefix]:03d}"

    client = FakeClient()
    service = ExecutionService(
        case_store=cases, record_store=records, artifact_root=tmp_path,
        driver=AwsS3VersioningCloudFormationDriver(
            client, id_factory=ids, sleeper=lambda seconds: None),
        monitor=AwsS3VersioningHealthMonitor(client),
        probes=(AwsS3VersioningProbe(client),),
        runtime=RecordedContractRuntime({
            "PostChangeReview.v1": {"output": {
                "decision": "accept",
                "summary": "The approved bucket now has versioning enabled.",
                "validated_outcomes": ["GetBucketVersioning reports Enabled"],
                "residual_risks": ["older object versions add storage cost"],
                "handoff_notes": ["retain the 15-minute deployment freeze evidence"],
            }},
        }, now=lambda: "2026-09-03T00:00:00Z"),
        now=lambda: "2026-09-03T00:00:00Z", id_factory=ids)
    outcome = service.execute(
        approved.case_id, originator="shasta-owner", execution_job_id="JOB-1")
    assert outcome.case.state is CaseState.REMEDIATED
    assert outcome.rolled_back is False
    assert outcome.contained is False
    assert client.current_versioning == "Enabled"
    certificate_id = outcome.case.record_ids["remediation_certificate_id"]
    certificate = records.get(certificate_id)
    assert certificate.body["finding_ids"] == ("FIND-1",)
    assert certificate.body["completed_status"] == "remediated"
