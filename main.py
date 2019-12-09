def createMsg(data, dest):
    import json, os

    with open(dest["metaTemplate"]) as json_file:
        msg = json.load(json_file)

    files = {}
    filename = data['name'] + ":" + data['bucket']
    sizeBytes = data['size']
    md5hash = data['md5Hash']
    manifestCreated = data['timeCreated']
    fullSizeMegabytes = "{:.6f}".format(int(data['size'])/1000000)
    files["sizeBytes"] = f"{sizeBytes}"
    files["name"] = f"{filename}"
    files["md5hash"] = f"{md5hash}"
    files["relativePath"] = ".\\"
    msg['files'] = f"{files}"
    msg["manifestCreated"] = f"{manifestCreated}"
    msg["fullSizeMegabytes"] = f"{fullSizeMegabytes}"
    return msg

def pubFileMetaData(data, context):
    import os
    
    from google.cloud import pubsub_v1
    project_id = os.environ['PROJECT_ID']
    if(project_id): 
        dest = {}
        topic_name = "blaise-dev-258914-export-topic"
        fileExtn = data['name'].split(".")[1].lower()
        runPubSub = False
        if (fileExtn == "csv"):
            runPubSub = True
            metaTemplate = os.getcwd + "\mi-meta-template.json"
            dest["metaTemplate"] = f"{metaTemplate}"
            dest["iterationL2"] = f"{''}"
            dest["iterationL3"] = f"{''}"
            dest["iterationL4"] = f"{''}"  

        elif fileExtn == "asc" or fileExtn == "rmk" or fileExtn == "sps":
            runPubSub = True
            metaTemplate = os.getcwd + "\dde-meta-template.json"
            # File needs to be in the format of opn1911a.sps
            dest["metaTemplate"] = f"{metaTemplate}"
            dest["iterationL2"] = f"{data['name'][:3]}"
            dest["iterationL3"] = f"{data['name'][3:7]}"
            dest["iterationL4"] = f"{data['name'][7:8]}"  
        else:
            runPubSub = False
            print("Error: Filetype {} not found for DDE or MI".format(fileExtn))

        if (runPubSub):
            client = pubsub_v1.PublisherClient()
            topic_path = client.topic_path(project_id, topic_name)
            msg = createMsg(data, dest)
            msgbytes = bytes(json.dumps(msg), encoding='utf-8')
            client.publish(topic_path, data=msgbytes)
