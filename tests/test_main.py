import json
import os
import blaise_dds
import pytest

from google.cloud.pubsub_v1 import PublisherClient
from utils import InvalidFileExtension, InvalidFileType
from unittest import mock
from main import (
    publishMsg,
    size_in_megabytes,
    update_data_delivery_state,
    create_message,
    send_pub_sub_message,
)


@mock.patch.dict(
    os.environ,
    {
        "PROJECT_ID": "test_project_id",
        "ENV": "test",
        "TOPIC_NAME": "nifi-notify",
        "ON-PREM-SUBFOLDER": "DEV",
    },
)
@mock.patch.object(blaise_dds.Client, "update_state")
@mock.patch.object(PublisherClient, "publish")
@pytest.mark.parametrize(
    "instrument, expected_message",
    [
        ("LMC2102R", pytest.lazy_fixture("expected_pubsub_message_lmc")),
        ("OPN2102R", pytest.lazy_fixture("expected_pubsub_message_opn")),
        ("LMS2102R", pytest.lazy_fixture("expected_pubsub_message_lms")),
    ],
)
def test_publishMsg_dd(
    mock_pubsub, mock_update_state, dd_event, instrument, expected_message
):
    dd_event = dd_event(instrument)

    publishMsg(dd_event, None)
    assert mock_update_state.call_count == 2
    assert mock_update_state.call_args_list[0] == mock.call(
        dd_event["name"],
        "in_nifi_bucket",
        None,
    )
    assert mock_update_state.call_args_list[1] == mock.call(
        dd_event["name"],
        "nifi_notified",
        None,
    )
    assert len(mock_pubsub.call_args_list) == 1
    assert (
        mock_pubsub.call_args_list[0][0][0]
        == "projects/test_project_id/topics/nifi-notify"
    )
    pubsub_message = mock_pubsub.call_args_list[0][1]["data"]
    assert json.loads(pubsub_message) == expected_message


@mock.patch.dict(
    os.environ,
    {
        "PROJECT_ID": "test_project_id",
        "ENV": "test",
        "TOPIC_NAME": "nifi-notify",
        "ON-PREM-SUBFOLDER": "DEV",
    },
)
@mock.patch.object(blaise_dds.Client, "update_state")
@mock.patch.object(PublisherClient, "publish")
def test_publishMsg_mi(mock_pubsub, mock_update_state, mi_event):
    publishMsg(mi_event, None)
    assert mock_update_state.call_count == 2
    assert mock_update_state.call_args_list[0] == mock.call(
        mi_event["name"],
        "in_nifi_bucket",
        None,
    )
    assert mock_update_state.call_args_list[1] == mock.call(
        mi_event["name"],
        "nifi_notified",
        None,
    )

    assert (
        mock_pubsub.call_args_list[0][0][0]
        == "projects/test_project_id/topics/nifi-notify"
    )
    pubsub_message = mock_pubsub.call_args_list[0][1]["data"]
    assert json.loads(pubsub_message) == {
        "version": 3,
        "schemaVersion": 1,
        "files": [
            {
                "sizeBytes": "20",
                "name": "mi_foobar.zip:ons-blaise-v2-nifi",
                "md5sum": "d1ad7875be9ee3c6fde3b6f9efdf3c6b67fad78ebd7f6dbc",
                "relativePath": ".\\",
            }
        ],
        "sensitivity": "High",
        "sourceName": "gcp_blaise_test",
        "description": "Management Information files uploaded to GCP bucket from Blaise5",
        "dataset": "blaise_mi",
        "iterationL1": "DEV",
        "iterationL2": "",
        "iterationL3": "",
        "iterationL4": "",
        "manifestCreated": "0103202021_16428",
        "fullSizeMegabytes": "0.000020",
    }


@mock.patch.dict(
    os.environ,
    {"PROJECT_ID": "test_project_id", "ENV": "test", "TOPIC_NAME": "nifi-notify"},
)
@mock.patch.object(blaise_dds.Client, "update_state")
@mock.patch.object(PublisherClient, "publish")
@pytest.mark.parametrize(
    "instrument",
    [
        ("LMC2102R"),
        ("OPN2102R"),
        ("LMS2102R"),
    ],
)
def test_publishMsg_error(mock_pubsub, mock_update_state, dd_event, instrument):
    mock_pubsub.side_effect = Exception(
        "Explosions occurred when sending message to pubsub"
    )
    dd_event = dd_event(instrument)
    publishMsg(dd_event, None)
    assert mock_update_state.call_count == 2
    assert mock_update_state.call_args_list[0] == mock.call(
        dd_event["name"],
        "in_nifi_bucket",
        None,
    )
    assert mock_update_state.call_args_list[1] == mock.call(
        dd_event["name"],
        "errored",
        "Exception('Explosions occurred when sending message to pubsub')",
    )


@mock.patch.dict(
    os.environ,
    {"TOPIC_NAME": "nifi-notify"},
)
@mock.patch.object(blaise_dds.Client, "update_state")
@pytest.mark.parametrize(
    "instrument",
    [
        ("LMC2102R"),
        ("OPN2102R"),
        ("LMS2102R"),
    ],
)
def test_project_id_not_set(mock_update_state, dd_event, capsys, instrument):
    dd_event = dd_event(instrument)

    publishMsg(dd_event, None)
    assert mock_update_state.call_count == 1
    assert mock_update_state.call_args_list[0] == mock.call(
        dd_event["name"],
        "in_nifi_bucket",
        None,
    )
    captured = capsys.readouterr()
    assert captured.out == (
        "Configuration: Project ID: None\n"
        + "Configuration: Topic Name: nifi-notify\n"
        + "Configuration: ON-PREM-SUBFOLDER: None\n"
        + "Configuration: Env: None\n"
        + f"Configuration: File name: dd_{instrument}_0103202021_16428.zip\n"
        + "Configuration: Bucket Name: ons-blaise-v2-nifi\n"
        + "project_id not set, publish failed\n"
    )


@pytest.mark.parametrize(
    "size_in_bytes,size_in_megs",
    [
        ("20", "0.000020"),
        ("320", "0.000320"),
        ("4783", "0.004783"),
        ("12004783", "12.004783"),
        ("3475231", "3.475231"),
    ],
)
def test_size_in_megabytes(size_in_bytes, size_in_megs):
    assert size_in_megabytes(size_in_bytes) == size_in_megs


@mock.patch.object(blaise_dds.Client, "update_state")
@pytest.mark.parametrize(
    "instrument,state",
    [
        ("LMC2102R", "in_nifi_bucket"),
        ("OPN2102R", "nifi_notified"),
        ("LMS2102R", "in_arc"),
    ],
)
def test_update_data_delivery_state(mock_update_state, dd_event, instrument, state):
    dd_event = dd_event(instrument)
    update_data_delivery_state(dd_event, state)
    assert mock_update_state.call_count == 1
    assert mock_update_state.call_args_list[0] == mock.call(
        dd_event["name"],
        state,
        None,
    )


@pytest.mark.parametrize(
    "instrument,foolish_state",
    [
        ("LMC2102R", "in_kfc_bucket"),
        ("OPN2102R", "hifi_notified"),
        ("LMS2102R", "noah_is_in_the_arc"),
    ],
)
def test_update_data_delivery_state_invalid_state(
    dd_event, instrument, foolish_state, capsys
):
    dd_event = dd_event(instrument)
    update_data_delivery_state(dd_event, foolish_state)
    captured = capsys.readouterr()
    assert (
        captured.out
        == "failed to update dds state: Invalid URL 'None/v1/state/descriptions': No schema supplied. Perhaps you meant http://None/v1/state/descriptions?\n"
    )


@mock.patch.object(blaise_dds.Client, "update_state")
@pytest.mark.parametrize(
    "instrument,state",
    [
        ("LMC2102R", "in_nifi_bucket"),
        ("OPN2102R", "nifi_notified"),
        ("LMS2102R", "in_arc"),
    ],
)
def test_update_data_delivery_state_fail(
    mock_update_state, dd_event, capsys, instrument, state
):
    mock_update_state.side_effect = Exception(
        "Computer says no. Do not pass Go. Do not collect £200"
    )
    dd_event = dd_event(instrument)
    update_data_delivery_state(dd_event, state)
    captured = capsys.readouterr()
    assert (
        captured.out
        == "failed to update dds state: Computer says no. Do not pass Go. Do not collect £200\n"
    )


def test_create_message_mi(mi_event, config):
    actual_message = create_message(mi_event, config)
    assert (
        actual_message.description
        == "Management Information files uploaded to GCP bucket from Blaise5"
    )
    assert actual_message.dataset == "blaise_mi"
    assert actual_message.iterationL1 == "OPN"
    assert actual_message.iterationL2 == ""


def test_create_message_dd_opn(dd_event, config, file):
    file.name = f"dd_OPN2101A.zip:my-bucket-name"

    dd_event = dd_event("OPN2101A")
    actual_message = create_message(dd_event, config)

    assert (
        actual_message.description
        == "Data Delivery files for OPN uploaded to GCP bucket from Blaise5"
    )
    assert actual_message.dataset == "blaise_dde"
    assert actual_message.iterationL1 == "SYSTEMS"
    assert actual_message.iterationL2 == config.on_prem_subfolder
    assert actual_message.iterationL3 == "OPN"
    assert actual_message.iterationL4 == "OPN2101A"


@pytest.mark.parametrize(
    "instrument,expected_survey_name",
    [
        ("LMS2102_A1", "LMS"),
        ("lms2102_bk1", "LMS"),
        ("lmc2102_bk1", "LMC"),
        ("lmb21021_bk2", "LMB"),
    ],
)
def test_create_message_dd_lms(
    instrument, expected_survey_name, dd_event, config, file
):
    file.name = f"dd_{instrument}.zip:my-bucket-name"
    dd_event = dd_event(instrument)
    actual_message = create_message(dd_event, config)

    assert (
        actual_message.description
        == f"Data Delivery files for {expected_survey_name} uploaded to GCP bucket from Blaise5"
    )
    assert actual_message.dataset == "blaise_dde"
    assert actual_message.iterationL1 == "LMS_Master"
    assert actual_message.iterationL2 == "CLOUD"
    assert actual_message.iterationL3 == config.env
    assert actual_message.iterationL4 == instrument.upper()


@pytest.mark.parametrize(
    "spicy_file_extension",
    [
        ("avi"),
        ("dat"),
        ("nth"),
        ("zoo"),
        ("qxd"),
    ],
)
def test_create_message_invalid_file_extension(spicy_file_extension, dd_event, config):
    dd_event = dd_event("OPN2101A")
    dd_event["name"] = f"dd_opn2101a.{spicy_file_extension}:my-bucket-name"

    with pytest.raises(InvalidFileExtension):
        create_message(dd_event, config)


@pytest.mark.parametrize(
    "spicy_file_types",
    [
        ("notMI"),
        ("notDD"),
        ("ddfoo"),
        ("mibar"),
        ("mmmm_spicy"),
    ],
)
def test_create_message_invalid_file_type(spicy_file_types, dd_event, config):
    dd_event = dd_event("OPN2101A")
    dd_event["name"] = f"{spicy_file_types}_opn2101a.zip:my-bucket-name"

    with pytest.raises(InvalidFileType):
        create_message(dd_event, config)


@mock.patch.object(PublisherClient, "publish")
def test_send_pub_sub_message(
    mock_pubsub, config, message, expected_pubsub_message_foo
):
    send_pub_sub_message(config, message)

    assert len(mock_pubsub.call_args_list) == 1
    assert mock_pubsub.call_args_list[0][0][0] == "projects/foobar/topics/barfoo"
    pubsub_message = mock_pubsub.call_args_list[0][1]["data"]
    assert json.loads(pubsub_message) == expected_pubsub_message_foo
