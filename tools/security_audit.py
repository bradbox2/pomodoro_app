import os
import re
import sys

# 检测配置
EXTENSIONS = ['.py', '.json', '.md', '.bat', '.sh', '.spec', '.txt']
EXCLUDE_DIRS = ['.git', '.venv', '__pycache__', 'node_modules']

# 正则表达式
PATTERNS = {
    'IP Address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    'Secret/Key Assignment': r'(?i)(password|passwd|secret|api_key|access_token|token|auth|credential|login_pass)\s*[:=]\s*["\']([^"\']+)["\']',
    'Private Config/URL': r'https?://[^\s<>"]+|localhost:\d+',
}

def scan_file(file_path):
    findings = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            for line_no, content in enumerate(lines, 1):
                for label, pattern in PATTERNS.items():
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        # 排除常见的非敏感 IP (如 127.0.0.1)
                        match_text = match.group(0)
                        if label == 'IP Address' and (match_text.startswith('127.0.') or match_text.startswith('0.0.')):
                            continue
                        
                        # 如果是赋值语句，提取具体的值进行展示
                        secret_value = match.group(2) if label == 'Secret/Key Assignment' else match_text
                        findings.append({
                            'label': label,
                            'line': line_no,
                            'text': content.strip(),
                            'value': secret_value,
                            'full_match': match.group(0)
                        })
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return findings

def interactive_handle(file_path, findings):
    if not findings:
        return

    print(f"\n[!] Found {len(findings)} issues in: {file_path}")
    new_lines = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        new_lines = f.readlines()

    modified = False
    for item in findings:
        print(f"--- Finding at Line {item['line']} ---")
        print(f"Type: {item['label']}")
        print(f"Content: {item['text']}")
        print(f"Suspected Value: {item['value']}")
        
        choice = input("\nAction: [k]Keep, [m]Mask/Redact, [s]Skip this file: ").lower()
        
        if choice == 'm':
            # 替换逻辑
            line_idx = item['line'] - 1
            old_line = new_lines[line_idx]
            new_line = old_line.replace(item['value'], "###REDACTED###")
            new_lines[line_idx] = new_line
            modified = True
            print("Done: Value masked in memory.")
        elif choice == 's':
            return False

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"[+] File {file_path} updated.")
    
    return True

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"Starting security scan in: {root_dir}")
    
    for root, dirs, files in os.walk(root_dir):
        # 排除目录
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if any(file.endswith(ext) for ext in EXTENSIONS):
                file_path = os.path.join(root, file)
                # 跳过本脚本
                if __file__ in file_path:
                    continue
                    
                findings = scan_file(file_path)
                if findings:
                    if not interactive_handle(file_path, findings):
                        print(f"Skipping {file_path}...")

    print("\nScan completed.")

if __name__ == "__main__":
    main()
