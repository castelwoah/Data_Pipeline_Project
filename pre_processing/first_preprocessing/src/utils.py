import re, datetime, pytz, subprocess, os, json
from botocore.exceptions import ClientError
from time import gmtime, strftime

def log(msg, flag=None, path="./logs"):
    if flag==None:
        flag = 0
    head = ["DEBUG", "ERROR", "WARN", "STATUS", "INFO"]
    now = strftime("%H:%M:%S", gmtime())
    
    if not os.path.isdir(path):
        os.mkdir(path)
    
    if not os.path.isfile(f"{path}/{head[flag]}.log"):
        assert subprocess.call(f"echo \"[{now}][{head[flag]}] > {msg}\" > {path}/{head[flag]}.log", shell=True)==0, print(f"[ERROR] > shell command failed to execute")
    else: assert subprocess.call(f"echo \"[{now}][{head[flag]}] > {msg}\" >> {path}/{head[flag]}.log", shell=True)==0, print(f"[ERROR] > shell command failed to execute")

# s3 client를 통해 해당 path의 file 목록 가져오기
def get_bucket_metadata(s3_client, pull_bucket_name, target_folder_prefix):
    # 특정 폴더 내 파일 목록 가져오기
    response = s3_client.list_objects_v2(Bucket=pull_bucket_name, Prefix=target_folder_prefix, Delimiter='/')

    if 'Contents' in response:
        return [obj for obj in response['Contents']]
    else:
        #print("No objects found in the folder.")
        return None

# 로컬 시간대(UTC+9)로 현재 날짜 설정
def get_curr_kst_time():
    return datetime.datetime.now(pytz.timezone('Asia/Seoul')).date()

# kst timezone 설정
def set_kst_timezone():
    return pytz.timezone('Asia/Seoul')

# 파싱을 위해 unuseal line terminators 제거
def remove_unusual_line_terminators(text):
    return re.sub(r'[\r\u2028\u2029]+', ' ', text)

# 정규 표현식을 사용하여 한글, 영어 알파벳, 숫자, 공백을 제외한 모든 문자를 공백으로 치환
def replace_special_to_space(text, pattern=r'[^a-zA-Z0-9가-힣\s]'):
    return re.sub(pattern, ' ', text)

def remove_multiful_space(text):
    return (' '.join(text.split())).strip()

def change_slash_format(text):
    return text.replace(" /", ",").replace("/", ",")

def change_str_to_timestamp(text):
    if text:
        return str(int(datetime.datetime.strptime(text, "%Y-%m-%d").timestamp()))
    else:
        return None

# unique id를 보관하는 S3 버킷의 obj_ids.json 업데이트
def update_ids_to_s3(s3_client, buket_name, prefix, upload_id_list):
    odd_id_list = get_id_from_s3(s3_client, buket_name, "obj_ids.json")
    new_id_list = list(set(odd_id_list + upload_id_list))
    update_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    data = {
        "version": "2024-09-04",
        "statement": "id_list_of_precessed_data_objects",
        "ids": new_id_list,
        "last_update": update_date
    }
    json_string = json.dumps(data)
    response = s3_client.put_object(
        Bucket=buket_name,          # 버킷 이름
        Key=prefix,             # 업로드할 파일의 키(경로 및 이름)
        Body=json_string,               # 업로드할 파일의 내용
        ContentType='application/json'  # 파일의 MIME 타입
    )
    
    return response

# unique id를 보관하는 S3 버킷의 obj_ids.json에서 id 목록 호출
def get_id_from_s3(s3_client, buket_name, prefix):
    metadata_list = get_bucket_metadata(s3_client, buket_name, prefix)
    if metadata_list:
        try:
            _obj = metadata_list[0]
            response = s3_client.get_object(Bucket=buket_name, Key=_obj['Key'])
            json_context = response['Body'].read().decode('utf-8')
            join_dict = json.loads(json_context)
            return join_dict.get('ids')
        except json.JSONDecodeError as e:
            #logging.error(f"JSONDecodeError encountered: {e}")
            return False
        except ClientError as e:
            #logging.error(f"ClientError encountered: {e}")
            return False
        except Exception as e:
            #logging.error(f"Unknow Error. encountered: {e}")
            return False

# unique id 목록과 현재 df의 id column을 비교하여 unique id 목록에 없는 id column 값만 list로 반환
def remove_duplicate_id(s3_client, buket_name, _df):
    id_list = get_id_from_s3(s3_client, buket_name, "obj_ids.json")
    df_id_list = _df['id'].unique().tolist()
    if id_list:
        unput_id_list = [id for id in df_id_list if id not in id_list]
        return unput_id_list
    else:
        return df_id_list
