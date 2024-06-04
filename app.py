from flask import Flask, request, jsonify, send_file
import os
import subprocess
import paramiko
import tarfile
import openai

app = Flask(__name__)
UPLOAD_FOLDER = '/path/to/upload'
OPTIMIZED_FOLDER = '/path/to/optimized'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OPTIMIZED_FOLDER'] = OPTIMIZED_FOLDER
openai.api_key = 'your-openai-api-key'

@app.route('/upload', methods=['GET','POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.tar'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        deploy_and_test(file_path)
        optimized_tarball = create_optimized_tarball(file_path)
        return send_file(optimized_tarball, as_attachment=True)
    return jsonify({'error': 'Invalid file type'}), 400

def deploy_and_test(file_path):
    server_ip = 'your-cloud-server-ip'
    username = 'your-username'
    key_path = '/path/to/your-key.pem'

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(server_ip, username=username, key_filename=key_path)

    sftp = ssh_client.open_sftp()
    sftp.put(file_path, '/home/your-username/' + os.path.basename(file_path))
    sftp.close()

    commands = [
        f'tar -xvf /home/your-username/{os.path.basename(file_path)} -C /home/your-username/',
        f'docker load -i /home/your-username/image.tar',
        'docker run -d --name your-container-name -p 80:5000 your-docker-image-name'
    ]

    for command in commands:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        stdout.channel.recv_exit_status()  # Wait for the command to complete
        print(stdout.read().decode())
        print(stderr.read().decode())

    traffic_command = 'ab -n 10000 -c 100 http://localhost:80/'
    stdin, stdout, stderr = ssh_client.exec_command(traffic_command)
    stdout.channel.recv_exit_status()
    print(stdout.read().decode())
    print(stderr.read().decode())

    logs_command = 'docker logs your-container-name'
    stdin, stdout, stderr = ssh_client.exec_command(logs_command)
    logs = stdout.read().decode()
    print(logs)

    ssh_client.close()

    analyze_performance_and_optimize(logs, file_path)

def analyze_performance_and_optimize(logs, file_path):
    suggestions = llm_analyze_logs(logs)
    apply_optimizations(file_path, suggestions)

def llm_analyze_logs(logs):
    response = openai.Completion.create(
        engine="davinci-codex",
        prompt=f"Analyze the following server logs and suggest optimizations for scalability:\n\n{logs}",
        max_tokens=500
    )
    suggestions = response.choices[0].text.strip()
    return suggestions.split('\n')

def apply_optimizations(file_path, suggestions):
    for suggestion in suggestions:
        file_to_modify, modification = parse_suggestion(suggestion)
        with open(os.path.join(file_path, file_to_modify), 'a') as file:
            file.write(f"\n# Optimization Suggestion: {modification}")

def parse_suggestion(suggestion):
    parts = suggestion.split(':')
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return "Dockerfile", suggestion  # Default case

def create_optimized_tarball(file_path):
    optimized_tar_path = os.path.join(app.config['OPTIMIZED_FOLDER'], 'optimized_' + os.path.basename(file_path))
    with tarfile.open(optimized_tar_path, "w") as tar:
        tar.add(file_path, arcname=os.path.basename(file_path))
    return optimized_tar_path

@app.route('/')
def index():
    return 'Hello, World!'


if __name__ == '__main__':
    app.run(debug=True)
