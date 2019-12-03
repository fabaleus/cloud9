# Compare a file on S3 to see if we have the latest version
# If not, upload it and invalidate CloudFront

import os
import boto3
import pprint
import json
import datetime
import time
import zipfile

# Where source is checked out
SOURCE_DIR  = '/tmp/jobs'
BUCKET_NAME = 'globiq-talenddeploy'
TALENDFILE = "core_SESSQSNewEmail_0.1.zip"
TALENDJOB = TALENDFILE[:TALENDFILE.rfind("_")]
print ("check for newer definition of: "+ TALENDJOB)

# Connect to S3 and get bucket
s3 = boto3.client('s3', region_name = "eu-west-1")
s3_resp = s3.head_object(Bucket=BUCKET_NAME, Key=TALENDFILE)
#pprint.pprint(s3_resp)
s3modified = s3_resp['LastModified']
modTime = time.mktime(s3modified.timetuple())
#print("modTime: "+str(modTime))

# check the local file
fileName = SOURCE_DIR+'/'+TALENDFILE
if not os.path.exists(SOURCE_DIR):
    os.makedirs(SOURCE_DIR)
if (os.path.isfile(fileName)):
    t = os.path.getmtime(fileName)
    fmodified = datetime.datetime.fromtimestamp(t)

print("file lastmodified: " + fmodified.strftime("%m/%d/%Y, %H:%M:%S"))
print("S3   lastmodified: " + s3modified.strftime("%m/%d/%Y, %H:%M:%S"))

# Compare them to S3 checksums
if fmodified.strftime("%m/%d/%Y, %H:%M:%S") != s3modified.strftime("%m/%d/%Y, %H:%M:%S"):
    print("download " + fileName)
    s3.download_file(BUCKET_NAME, TALENDFILE, fileName)
    
    # Showing stat information of file
    stinfo = os.stat(fileName)
    print (stinfo)
    
    #update the modifiecation time
    os.utime(fileName, (modTime, modTime))
    
    # print the updated info
    # print (time.asctime( time.localtime(stinfo.st_atime)))
    
    # unzip the job
    with zipfile.ZipFile(fileName,"r") as zip_ref:
        zip_ref.extractall(SOURCE_DIR)
else:
    print(fileName+" is up-to-date")
    