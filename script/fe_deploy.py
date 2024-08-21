import json
import paramiko
import os
import tarfile
from scp import SCPClient

config_path = r"D:\apps\桌面\my_server.json"
work_dist_dir = r"F:\code\fe\vue-vben-admin\apps\web-antd\dist"
app_path = "/opt/app/admin/dist"

# 读取JSON配置文件
with open(config_path, 'r') as f:
    config = json.load(f)

hostname = config['host']
username = config['user']
password = config['pass']

# 创建本地打包文件
local_tar_file = 'app_files.tar.gz'
os.chdir(work_dist_dir)
with tarfile.open(local_tar_file, 'w:gz') as tar:
    tar.add('.', arcname='.')

# 创建SSH客户端并连接到远程服务器
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname, username=username, password=password)

    # 清空远程的app_path目录
    print(f"Clearing the remote directory: {app_path}...")
    stdin, stdout, stderr = client.exec_command(f'rm -rf {app_path}/*')
    print(stdout.read().decode())
    print(stderr.read().decode())

    # 使用SCP传输打包文件到远程服务器
    print(f"Transferring {local_tar_file} to remote server...")
    scp = SCPClient(client.get_transport())
    scp.put(local_tar_file, app_path)

    # 解压传输的文件到远程的app_path目录
    print(f"Extracting {local_tar_file} on remote server...")
    stdin, stdout, stderr = client.exec_command(f'tar -xzf {app_path}/{local_tar_file} -C {app_path}')
    print(stdout.read().decode())
    print(stderr.read().decode())

    # 删除远程的tar.gz文件
    stdin, stdout, stderr = client.exec_command(f'rm {app_path}/{local_tar_file}')
    print(stdout.read().decode())
    print(stderr.read().decode())

finally:
    # 关闭SCP和SSH连接
    scp.close()
    client.close()

    # 删除本地的tar.gz文件
    os.remove(local_tar_file)

    print("Deployment complete.")
