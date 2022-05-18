import json
import boto3, csv, os
from statistics import mean
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart



def get_running_instances():
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['pending', 'running', ]}, ])
    return [instance.id for instance in instances]
    
def get_idle_instances():
    instance_cpu_data={}
    ids = get_running_instances()
    client = boto3.client('cloudwatch')
    dnow = datetime.now()
    for id in ids:
        response = client.get_metric_data(
            MetricDataQueries=[
               {
                    'Id': 'myrequest',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/EC2',
                            'MetricName': 'CPUUtilization',
                            'Dimensions': [
                                {
                                    'Name': 'InstanceId',
                                    'Value': id
                                }
                            ]
                        },
                        'Period': 3600,
                        'Stat': 'Average',
                        'Unit': 'Percent'
                    }
                },
            ],
            StartTime=datetime.now() - timedelta(days=1),
            EndTime=datetime.now()
        )
        
        for MetricDataResults in response['MetricDataResults']:
            list_avg = mean(MetricDataResults['Values'])
            instance_cpu_data[id] = list_avg
    return instance_cpu_data



def lambda_handler(event, context):
    instance_cpu_data = get_idle_instances()
    print(instance_cpu_data)
    filename =  "CPU-Usage_"+datetime.now().strftime("%d%m%Y%H%M%S") + ".csv"
    header_csv = ['INSTANCE-ID','AVERAGE-CPU-UTILIZATION']
    fo=open("/tmp/"+filename,"a",newline='')
    csv_w = csv.writer(fo)
    csv_w.writerow(header_csv)
    print(instance_cpu_data)
    for data in instance_cpu_data:
        csv_w.writerow([data,instance_cpu_data[data]])
    fo.close()
    client = boto3.client('ses')
    message = MIMEMultipart()
    message['Subject'] = "CPU Utilization Report for the EC2 Instances"
    message['From'] = os.environ['FROM_EMAIL']
    message['To'] = ', '.join(os.environ['TO_EMAIL'].split(','))
    part = MIMEText("""Hi,
    Please find the attached CPU Utilization CSV File for the day %s
    Best regards
    Your friendly Reminder""" % (datetime.now().strftime("%d-%m-%Y")))
    message.attach(part)
    part = MIMEApplication(open("/tmp/"+filename, 'rb').read())
    part.add_header('Content-Disposition', 'attachment', filename=filename)
    message.attach(part)
    response = client.send_raw_email(
            Source=message['From'],
            Destinations= os.environ['TO_EMAIL'].split(','),
            RawMessage={
                'Data': message.as_string()
            }
        )
        
