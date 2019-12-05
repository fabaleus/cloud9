import json
import os
import boto3
import sys
import botocore
import pprint
import datetime
import time
import zipfile
from datetime import date
from datetime import datetime
import subprocess

print('Loading function')
SOURCE_DIR  = '/tmp/jobs'
BUCKET_NAME = 'globiq-talenddeploy'
TALENDFILE = "core_SESSQSNewEmail_0.1.zip"
TALENDJOB = TALENDFILE[:TALENDFILE.rfind("_")]
DEBUG = False

print ("check for newer definition of: "+ TALENDJOB)

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    
    if 'body' in event:
        if isinstance(event.get('body'), dict): 
            payload = event.get('body')
        else:
            payload = json.loads(event.get('body'))
    else:
        payload = event
        
    if not payload.get('MessageId'):
        raise Exception('Missing MessageId')
    if not payload.get('ReceiptHandle'):
        raise Exception('Missing ReceiptHandle')
    if not payload.get('MD5OfBody'):
        raise Exception('Missing MD5OfBody')
    if not payload.get('Body'):
        raise Exception('Missing Body')
    
    if DEBUG: payload.update(S3start=datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))    
    getTalendJobFromS3(payload)
    if DEBUG: payload.update(S3end=datetime.now().strftime("%m/%d/%Y, %H:%M:%S")) 
    job_exec = SOURCE_DIR+'/'+TALENDJOB+'/'+TALENDJOB+'_run.sh --context_param MessageId='+payload['MessageId'] \
    + ' --context_param ReceiptHandle='+payload['ReceiptHandle'] \
    + ' --context_param MD5OfBody='+str(payload['MD5OfBody']) \
    + ' --context_param Body='+str(payload['Body']) 
    
    proc = subprocess.Popen(["sh "+ job_exec], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    payload.update(printoutput=str(out))

    if DEBUG: payload.update(Jobend=datetime.now().strftime("%m/%d/%Y, %H:%M:%S")) 
    return {
        'statusCode': 200,
        #'body': json.dumps('Success')
        'body': json.dumps(payload)
    }
    #raise Exception('Something went wrong')
    
def getTalendJobFromS3(payload):
    # Connect to S3 and get bucket
    s3 = boto3.client('s3', region_name = "eu-west-1")
    s3_resp = s3.head_object(Bucket=BUCKET_NAME, Key=TALENDFILE)
    #pprint.pprint(s3_resp)
    s3modified = date.today()
    s3modified = s3_resp['LastModified']
    modTime = time.mktime(s3modified.timetuple())
    #print("modTime: "+str(modTime))

    # check the local file
    fileName = SOURCE_DIR+'/'+TALENDFILE
    print ("check local file: "+fileName)
    if DEBUG: payload.update(fileName=fileName)
    
    fmodified = date.today()
    if not os.path.exists(SOURCE_DIR):
        os.makedirs(SOURCE_DIR)
    if (os.path.isfile(fileName)):
        t = os.path.getmtime(fileName)
        fmodified = datetime.fromtimestamp(t)

    print("file lastmodified: " + fmodified.strftime("%m/%d/%Y, %H:%M:%S"))
    print("S3   lastmodified: " + s3modified.strftime("%m/%d/%Y, %H:%M:%S"))
    if DEBUG: payload.update(fmodified=fmodified.strftime("%m/%d/%Y, %H:%M:%S"))
    if DEBUG: payload.update(s3modified=s3modified.strftime("%m/%d/%Y, %H:%M:%S"))
    
    # Compare them to S3 checksums
    if fmodified.strftime("%m/%d/%Y, %H:%M:%S") != s3modified.strftime("%m/%d/%Y, %H:%M:%S"):
        print("download " + fileName)
        if DEBUG: payload.update(message='download file from s3')
        
        s3.download_file(BUCKET_NAME, TALENDFILE, fileName)
    
        # Showing stat information of file
        stinfo = os.stat(fileName)
        #print (stinfo)
    
        #update the modifiecation time
        os.utime(fileName, (modTime, modTime))
    
        # print the updated info
        # print (time.asctime( time.localtime(stinfo.st_atime)))
    
        # unzip the job
        with zipfile.ZipFile(fileName,"r") as zip_ref:
            zip_ref.extractall(SOURCE_DIR)
    else:
        print(fileName+" is up-to-date")
        if DEBUG: payload.update(message=fileName+' is up-to-date')
    
