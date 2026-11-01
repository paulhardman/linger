"""Build the unsigned Linger Apple Shortcut, then sign it:

    python3 make_shortcut.py [server-url] [out]
    shortcuts sign --mode anyone --input Linger-unsigned.shortcut --output ../Linger.shortcut
"""
import plistlib
import sys
import uuid

SERVER = sys.argv[1] if len(sys.argv) > 1 else "http://10.0.0.202:5056/process"
OUT = sys.argv[2] if len(sys.argv) > 2 else "Linger-unsigned.shortcut"

U_URL, U_LIST, U_PICK, U_POST = (str(uuid.uuid4()).upper() for _ in range(4))


def text(s):
    return {"Value": {"string": s, "attachmentsByRange": {}}, "WFSerializationType": "WFTextTokenString"}


def text_ref(output_uuid, name):
    return {
        "Value": {"string": "￼", "attachmentsByRange": {
            "{0, 1}": {"Type": "ActionOutput", "OutputUUID": output_uuid, "OutputName": name}}},
        "WFSerializationType": "WFTextTokenString",
    }


def attach(value):
    return {"Value": value, "WFSerializationType": "WFTextTokenAttachment"}


def action(ident, **params):
    return {"WFWorkflowActionIdentifier": ident, "WFWorkflowActionParameters": params}


actions = [
    action("is.workflow.actions.comment",
           WFCommentActionText="Linger: share an audio file here to change its tempo (pitch preserved). "
                               "The text below is the address of your Linger server's /process endpoint."),
    action("is.workflow.actions.gettext", UUID=U_URL, WFTextActionText=SERVER),
    action("is.workflow.actions.list", UUID=U_LIST,
           WFItems=["70", "75", "80", "85", "90", "95", "105", "110", "120", "130"]),
    action("is.workflow.actions.choosefromlist", UUID=U_PICK,
           WFInput=attach({"Type": "ActionOutput", "OutputUUID": U_LIST, "OutputName": "List"}),
           WFChooseFromListActionPrompt="Speed (%) — under 100 is slower"),
    action("is.workflow.actions.downloadurl", UUID=U_POST,
           WFURL=text_ref(U_URL, "Text"),
           WFHTTPMethod="POST",
           WFHTTPBodyType="Form",
           ShowHeaders=False,
           WFFormValues={
               "Value": {"WFDictionaryFieldValueItems": [
                   {"WFItemType": 5, "WFKey": text("file"),
                    # file fields need the extra ParameterState wrapper; a bare attachment is silently dropped
                    "WFValue": {"Value": attach({"Type": "ExtensionInput"}),
                                "WFSerializationType": "WFTokenAttachmentParameterState"}},
                   {"WFItemType": 0, "WFKey": text("speed"), "WFValue": text_ref(U_PICK, "Chosen Item")},
               ]},
               "WFSerializationType": "WFDictionaryFieldValue",
           }),
    action("is.workflow.actions.previewdocument",
           WFInput=attach({"Type": "ActionOutput", "OutputUUID": U_POST, "OutputName": "Contents of URL"})),
]

shortcut = {
    "WFWorkflowClientVersion": "2302.0.4",
    "WFWorkflowMinimumClientVersion": 900,
    "WFWorkflowMinimumClientVersionString": "900",
    "WFWorkflowIcon": {"WFWorkflowIconStartColor": 463140863, "WFWorkflowIconGlyphNumber": 59446},
    "WFWorkflowTypes": ["ActionExtension"],
    "WFWorkflowInputContentItemClasses": ["WFAVAssetContentItem", "WFGenericFileContentItem"],
    "WFWorkflowHasShortcutInputVariables": True,
    "WFWorkflowOutputContentItemClasses": [],
    "WFWorkflowImportQuestions": [{
        "ActionIndex": 1,
        "Category": "Parameter",
        "ParameterKey": "WFTextActionText",
        "Text": "Address of your Linger server's /process endpoint",
        "DefaultValue": SERVER,
    }],
    "WFWorkflowActions": actions,
}

with open(OUT, "wb") as f:
    plistlib.dump(shortcut, f, fmt=plistlib.FMT_BINARY)
print("wrote", OUT)
