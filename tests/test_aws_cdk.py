import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from elcapitan.aws_cdk import (
    AwsCdkCloudFormationRunner, AwsCdkPlanningError, link_aws_cdk_s3_bucket,
    materialize_cdk_s3_versioning, verify_s3_versioning_template_change,
)


BUCKET = "training-assets"
BUCKET_ARN = f"arn:aws:s3:::{BUCKET}"
LOGICAL_ID = "AssetsBucketA1B2C3"


def deployed_template():
    return {
        "Resources": {
            LOGICAL_ID: {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": BUCKET,
                    "BucketEncryption": {"mode": "AES256"},
                },
                "DeletionPolicy": "Retain",
                "UpdateReplacePolicy": "Retain",
            },
            "Policy": {"Type": "AWS::S3::BucketPolicy", "Properties": {}},
        },
        "Outputs": {"Bucket": {"Value": {"Ref": LOGICAL_ID}}},
    }


def state_document():
    return {
        "format": "ElCapitanAwsCdkState.v1",
        "stack_name": "TrainingStatic",
        "logical_resource_id": LOGICAL_ID,
        "construct_id": "AppBucket",
        "source_path": "platform/lib/static-stack.ts",
        "module_path": "platform",
        "source_sha256": hashlib.sha256(source_text().encode()).hexdigest(),
        "account_id": "111122223333",
        "region": "us-east-1",
        "executor_role_arn": (
            "arn:aws:iam::111122223333:role/elcapitan-s3-versioning-executor"),
        "cloudformation_service_role_arn": None,
        "deployed_template": deployed_template(),
    }


def source_text():
    return """import * as s3 from 'aws-cdk-lib/aws-s3';

export class StaticStack {
  build() {
    this.appBucket = new s3.Bucket(this, 'AppBucket', {
      bucketName: `training-assets`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption:        s3.BucketEncryption.S3_MANAGED,
      enforceSSL:        true,
    });
  }
}
"""


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    source = root / "platform" / "lib" / "static-stack.ts"
    source.parent.mkdir(parents=True)
    source.write_text(source_text(), encoding="utf-8")
    (root / "platform" / "pnpm-lock.yaml").write_text(
        "lockfileVersion: '9.0'\n", encoding="utf-8")
    return root


def test_cdk_link_and_materialization_bind_exact_stack_resource(tmp_path):
    root = repository(tmp_path)
    link = link_aws_cdk_s3_bucket(
        root, provider="aws", resource_uid=BUCKET_ARN,
        state_document=state_document(),
        resource_types=("aws_s3_bucket_versioning",),
    )
    assert link.iac_engine == "aws_cdk_cloudformation"
    assert link.resource_address == f"TrainingStatic.{LOGICAL_ID}"
    assert link.rollback_mode == "containment"
    assert link.module_path == "platform"
    proposed = source_text().replace(
        "      enforceSSL:        true,",
        "      versioned:         true,\n      enforceSSL:        true,")
    changed = materialize_cdk_s3_versioning(
        original=source_text(), proposed=proposed, link=link)
    assert changed.count("versioned:         true") == 1
    assert changed.replace("      versioned:         true,\n", "") == source_text()


def test_template_scope_proof_builds_forward_and_containment_templates():
    deployed = deployed_template()
    proposed = json.loads(json.dumps(deployed))
    proposed["Resources"][LOGICAL_ID]["Properties"][
        "VersioningConfiguration"] = {"Status": "Enabled"}
    forward, rollback = verify_s3_versioning_template_change(
        deployed_template=deployed,
        proposed_template=proposed,
        logical_resource_id=LOGICAL_ID,
    )
    assert forward["Resources"][LOGICAL_ID]["Properties"][
        "VersioningConfiguration"] == {"Status": "Enabled"}
    assert rollback["Resources"][LOGICAL_ID]["Properties"][
        "VersioningConfiguration"] == {"Status": "Suspended"}


def test_template_scope_rejects_any_sibling_change():
    deployed = deployed_template()
    proposed = json.loads(json.dumps(deployed))
    proposed["Resources"][LOGICAL_ID]["Properties"][
        "VersioningConfiguration"] = {"Status": "Enabled"}
    proposed["Resources"]["Policy"]["Properties"]["Changed"] = True
    with pytest.raises(AwsCdkPlanningError, match="outside the approved"):
        verify_s3_versioning_template_change(
            deployed_template=deployed,
            proposed_template=proposed,
            logical_resource_id=LOGICAL_ID,
        )


def test_template_scope_does_not_deploy_preexisting_source_template_drift():
    deployed = deployed_template()
    deployed["Resources"]["Policy"]["Metadata"] = {"comment": "deployed"}
    baseline = deployed_template()
    baseline["Resources"]["Policy"]["Metadata"] = {"comment": "source"}
    proposed = json.loads(json.dumps(baseline))
    proposed["Resources"][LOGICAL_ID]["Properties"][
        "VersioningConfiguration"] = {"Status": "Enabled"}
    forward, _rollback = verify_s3_versioning_template_change(
        deployed_template=deployed,
        baseline_synthesized_template=baseline,
        proposed_template=proposed,
        logical_resource_id=LOGICAL_ID,
    )
    assert forward["Resources"]["Policy"]["Metadata"] == {"comment": "deployed"}


def test_cdk_link_rejects_wrong_live_bucket(tmp_path):
    root = repository(tmp_path)
    document = state_document()
    document["deployed_template"]["Resources"][LOGICAL_ID]["Properties"][
        "BucketName"] = "another-bucket"
    with pytest.raises(AwsCdkPlanningError, match="does not match"):
        link_aws_cdk_s3_bucket(
            root, provider="aws", resource_uid=BUCKET_ARN,
            state_document=document,
        )


def test_cdk_runner_synthesizes_without_ambient_cloud_credentials(
        tmp_path, monkeypatch):
    root = repository(tmp_path)
    link = link_aws_cdk_s3_bucket(
        root, provider="aws", resource_uid=BUCKET_ARN,
        state_document=state_document())
    source = root / link.source_path
    proposed_source = source_text().replace(
        "      enforceSSL:        true,",
        "      versioned:         true,\n      enforceSSL:        true,")
    source.write_text(materialize_cdk_s3_versioning(
        original=source_text(), proposed=proposed_source, link=link))
    proposed = deployed_template()
    proposed["Resources"][LOGICAL_ID]["Properties"][
        "VersioningConfiguration"] = {"Status": "Enabled"}
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[0] == "pnpm":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        document = (
            deployed_template()
            if str(argv[-1]).endswith("cdk_baseline_synth") else proposed)
        return SimpleNamespace(
            returncode=0, stdout=json.dumps(document), stderr="")

    monkeypatch.setattr("elcapitan.aws_cdk.subprocess.run", run)
    checks = AwsCdkCloudFormationRunner(
        ("cdk",), application_environment={
            "DOMAIN": "example.test",
            "AWS_PROFILE": "must-not-pass",
            "AWS_ACCESS_KEY_ID": "must-not-pass",
            "OPENAI_API_KEY": "must-not-pass",
        }).check(
            root, link, state_document=state_document(),
            original_source=source_text())
    assert [check.name for check in checks] == [
        "dependency_install", "cdk_baseline_synth", "cdk_synth",
        "cloudformation_scope", "rollback_template"]
    assert all(check.passed for check in checks)
    argv, kwargs = calls[1]
    assert "--no-lookups" in argv
    assert "--no-staging" not in argv
    assert kwargs["env"]["DOMAIN"] == "example.test"
    assert kwargs["env"]["CDK_DEFAULT_ACCOUNT"] == "111122223333"
    assert "AWS_PROFILE" not in kwargs["env"]
    assert "AWS_ACCESS_KEY_ID" not in kwargs["env"]
    assert "OPENAI_API_KEY" not in kwargs["env"]
    assert kwargs["env"]["HOME"] != os.environ.get("HOME")
    assert kwargs["env"]["AWS_SHARED_CREDENTIALS_FILE"] == os.devnull
    assert not (root / "platform" / "node_modules").exists()
